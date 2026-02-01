"""코드 파싱 및 청킹 유틸리티

함수/클래스 단위로 코드를 청킹하여 메타데이터와 함께 반환
"""

import os
import re
import ast
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


def get_code_base_path() -> str:
    """설정에서 코드베이스 경로 가져오기"""
    from config import get_settings
    return get_settings().code_base_path


# 대상 코드베이스 경로 (하위 호환성)
CODE_BASE_PATH = "/Volumes/DEV_DATA/code"

# 지원 확장자
SUPPORTED_EXTENSIONS = {".java", ".py", ".vue", ".js"}

# 무시할 디렉토리
IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "target", ".idea",
    ".gradle", "out", "bin", ".settings",
}

# 언어 매핑
EXTENSION_TO_LANGUAGE = {
    ".java": "java",
    ".py": "python",
    ".vue": "vue",
    ".js": "javascript",
}


@dataclass
class CodeChunk:
    """코드 청크 데이터 클래스"""
    content: str
    filepath: str
    language: str
    project: str
    chunk_type: str  # function, class, method, component, script
    name: str  # 함수/클래스 이름
    start_line: int
    end_line: int
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "filepath": self.filepath,
            "language": self.language,
            "project": self.project,
            "chunk_type": self.chunk_type,
            "name": self.name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            **self.metadata,
        }

    @property
    def id(self) -> str:
        """유니크 ID 생성"""
        return f"{self.filepath}::{self.name}::{self.start_line}"


def get_project_name(filepath: Path) -> str:
    """파일 경로에서 프로젝트명 추출"""
    try:
        relative = filepath.relative_to(CODE_BASE_PATH)
        parts = relative.parts
        if parts:
            return parts[0]
    except ValueError:
        pass
    return "unknown"


def scan_files(base_path: str = CODE_BASE_PATH) -> list[Path]:
    """대상 디렉토리에서 지원하는 파일 스캔"""
    files = []
    base = Path(base_path)

    if not base.exists():
        print(f"경고: 경로가 존재하지 않습니다: {base_path}")
        return files

    for root, dirs, filenames in os.walk(base):
        # 무시할 디렉토리 필터링
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for filename in filenames:
            filepath = Path(root) / filename
            if filepath.suffix in SUPPORTED_EXTENSIONS:
                files.append(filepath)

    return files


# =============================================================================
# Python 파서
# =============================================================================

def parse_python(filepath: Path, content: str) -> list[CodeChunk]:
    """Python 파일을 AST로 파싱하여 함수/클래스 단위 청킹"""
    chunks = []
    lines = content.splitlines()
    project = get_project_name(filepath)

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        # 파싱 실패시 전체 파일을 하나의 청크로
        return [CodeChunk(
            content=content,
            filepath=str(filepath),
            language="python",
            project=project,
            chunk_type="file",
            name=filepath.stem,
            start_line=1,
            end_line=len(lines),
            metadata={"parse_error": str(e)},
        )]

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            start = node.lineno - 1
            end = node.end_lineno
            class_content = "\n".join(lines[start:end])

            chunks.append(CodeChunk(
                content=class_content,
                filepath=str(filepath),
                language="python",
                project=project,
                chunk_type="class",
                name=node.name,
                start_line=node.lineno,
                end_line=end,
                metadata={
                    "decorators": [ast.unparse(d) for d in node.decorator_list],
                    "bases": [ast.unparse(b) for b in node.bases],
                },
            ))

        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # 클래스 내부 메서드는 별도로 처리하지 않음 (클래스 청크에 포함)
            parent = None
            for potential_parent in ast.walk(tree):
                if isinstance(potential_parent, ast.ClassDef):
                    for child in ast.iter_child_nodes(potential_parent):
                        if child is node:
                            parent = potential_parent
                            break

            if parent is None:  # 최상위 함수만
                start = node.lineno - 1
                end = node.end_lineno
                func_content = "\n".join(lines[start:end])

                chunks.append(CodeChunk(
                    content=func_content,
                    filepath=str(filepath),
                    language="python",
                    project=project,
                    chunk_type="function",
                    name=node.name,
                    start_line=node.lineno,
                    end_line=end,
                    metadata={
                        "decorators": [ast.unparse(d) for d in node.decorator_list],
                        "args": [arg.arg for arg in node.args.args],
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                    },
                ))

    # 청크가 없으면 전체 파일을 청크로
    if not chunks:
        chunks.append(CodeChunk(
            content=content,
            filepath=str(filepath),
            language="python",
            project=project,
            chunk_type="file",
            name=filepath.stem,
            start_line=1,
            end_line=len(lines),
        ))

    return chunks


# =============================================================================
# Java 파서
# =============================================================================

# Java 클래스/인터페이스 패턴
JAVA_CLASS_PATTERN = re.compile(
    r'^(\s*)((?:public|private|protected|abstract|final|static|\s)*)'
    r'(class|interface|enum|record)\s+(\w+)',
    re.MULTILINE
)

# Java 메서드 패턴
JAVA_METHOD_PATTERN = re.compile(
    r'^(\s*)((?:public|private|protected|static|final|abstract|synchronized|native|\s)*)'
    r'(?:<[^>]+>\s+)?'  # 제네릭
    r'(\w+(?:<[^>]+>)?(?:\[\])?)\s+'  # 반환 타입
    r'(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{',
    re.MULTILINE
)


def find_matching_brace(content: str, start_pos: int) -> int:
    """중괄호 매칭하여 끝 위치 반환"""
    brace_count = 0
    in_string = False
    string_char = None
    i = start_pos

    while i < len(content):
        char = content[i]

        # 문자열 처리
        if char in ('"', "'") and (i == 0 or content[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False

        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return i

        i += 1

    return len(content) - 1


def parse_java(filepath: Path, content: str) -> list[CodeChunk]:
    """Java 파일을 정규식으로 파싱하여 클래스/메서드 단위 청킹"""
    chunks = []
    lines = content.splitlines()
    project = get_project_name(filepath)

    # 클래스 찾기
    for match in JAVA_CLASS_PATTERN.finditer(content):
        class_type = match.group(3)  # class, interface, enum
        class_name = match.group(4)
        modifiers = match.group(2).strip()

        # 클래스 시작 위치
        start_pos = match.start()
        start_line = content[:start_pos].count('\n') + 1

        # 중괄호 찾기
        brace_pos = content.find('{', match.end())
        if brace_pos == -1:
            continue

        end_pos = find_matching_brace(content, brace_pos)
        end_line = content[:end_pos].count('\n') + 1

        class_content = content[start_pos:end_pos + 1]

        chunks.append(CodeChunk(
            content=class_content,
            filepath=str(filepath),
            language="java",
            project=project,
            chunk_type=class_type,
            name=class_name,
            start_line=start_line,
            end_line=end_line,
            metadata={
                "modifiers": modifiers,
            },
        ))

    # 청크가 없으면 전체 파일
    if not chunks:
        chunks.append(CodeChunk(
            content=content,
            filepath=str(filepath),
            language="java",
            project=project,
            chunk_type="file",
            name=filepath.stem,
            start_line=1,
            end_line=len(lines),
        ))

    return chunks


# =============================================================================
# Vue 파서
# =============================================================================

VUE_SCRIPT_PATTERN = re.compile(
    r'<script[^>]*>(.*?)</script>',
    re.DOTALL
)

VUE_TEMPLATE_PATTERN = re.compile(
    r'<template[^>]*>(.*?)</template>',
    re.DOTALL
)

VUE_STYLE_PATTERN = re.compile(
    r'<style[^>]*>(.*?)</style>',
    re.DOTALL
)


def parse_vue(filepath: Path, content: str) -> list[CodeChunk]:
    """Vue SFC를 template/script/style로 분리하여 청킹"""
    chunks = []
    lines = content.splitlines()
    project = get_project_name(filepath)
    component_name = filepath.stem

    # Script 추출
    script_match = VUE_SCRIPT_PATTERN.search(content)
    if script_match:
        script_content = script_match.group(0)
        start_line = content[:script_match.start()].count('\n') + 1
        end_line = content[:script_match.end()].count('\n') + 1

        chunks.append(CodeChunk(
            content=script_content,
            filepath=str(filepath),
            language="vue",
            project=project,
            chunk_type="script",
            name=f"{component_name}::script",
            start_line=start_line,
            end_line=end_line,
            metadata={"section": "script"},
        ))

    # Template 추출
    template_match = VUE_TEMPLATE_PATTERN.search(content)
    if template_match:
        template_content = template_match.group(0)
        start_line = content[:template_match.start()].count('\n') + 1
        end_line = content[:template_match.end()].count('\n') + 1

        chunks.append(CodeChunk(
            content=template_content,
            filepath=str(filepath),
            language="vue",
            project=project,
            chunk_type="template",
            name=f"{component_name}::template",
            start_line=start_line,
            end_line=end_line,
            metadata={"section": "template"},
        ))

    # 청크가 없으면 전체 파일
    if not chunks:
        chunks.append(CodeChunk(
            content=content,
            filepath=str(filepath),
            language="vue",
            project=project,
            chunk_type="component",
            name=component_name,
            start_line=1,
            end_line=len(lines),
        ))

    return chunks


# =============================================================================
# JavaScript 파서
# =============================================================================

JS_FUNCTION_PATTERN = re.compile(
    r'^(\s*)(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{',
    re.MULTILINE
)

JS_ARROW_FUNCTION_PATTERN = re.compile(
    r'^(\s*)(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>\s*\{',
    re.MULTILINE
)

JS_CLASS_PATTERN = re.compile(
    r'^(\s*)(?:export\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?\s*\{',
    re.MULTILINE
)


def parse_javascript(filepath: Path, content: str) -> list[CodeChunk]:
    """JavaScript 파일을 정규식으로 파싱하여 함수/클래스 단위 청킹"""
    chunks = []
    lines = content.splitlines()
    project = get_project_name(filepath)

    # 클래스 찾기
    for match in JS_CLASS_PATTERN.finditer(content):
        class_name = match.group(2)
        start_pos = match.start()
        start_line = content[:start_pos].count('\n') + 1

        brace_pos = content.find('{', match.end() - 1)
        end_pos = find_matching_brace(content, brace_pos)
        end_line = content[:end_pos].count('\n') + 1

        class_content = content[start_pos:end_pos + 1]

        chunks.append(CodeChunk(
            content=class_content,
            filepath=str(filepath),
            language="javascript",
            project=project,
            chunk_type="class",
            name=class_name,
            start_line=start_line,
            end_line=end_line,
        ))

    # 일반 함수 찾기
    for match in JS_FUNCTION_PATTERN.finditer(content):
        func_name = match.group(2)
        start_pos = match.start()
        start_line = content[:start_pos].count('\n') + 1

        brace_pos = content.find('{', match.end() - 1)
        end_pos = find_matching_brace(content, brace_pos)
        end_line = content[:end_pos].count('\n') + 1

        func_content = content[start_pos:end_pos + 1]

        chunks.append(CodeChunk(
            content=func_content,
            filepath=str(filepath),
            language="javascript",
            project=project,
            chunk_type="function",
            name=func_name,
            start_line=start_line,
            end_line=end_line,
        ))

    # 화살표 함수 찾기
    for match in JS_ARROW_FUNCTION_PATTERN.finditer(content):
        func_name = match.group(2)
        start_pos = match.start()
        start_line = content[:start_pos].count('\n') + 1

        brace_pos = content.find('{', match.end() - 1)
        end_pos = find_matching_brace(content, brace_pos)
        end_line = content[:end_pos].count('\n') + 1

        func_content = content[start_pos:end_pos + 1]

        chunks.append(CodeChunk(
            content=func_content,
            filepath=str(filepath),
            language="javascript",
            project=project,
            chunk_type="function",
            name=func_name,
            start_line=start_line,
            end_line=end_line,
        ))

    # 청크가 없으면 전체 파일
    if not chunks:
        chunks.append(CodeChunk(
            content=content,
            filepath=str(filepath),
            language="javascript",
            project=project,
            chunk_type="file",
            name=filepath.stem,
            start_line=1,
            end_line=len(lines),
        ))

    return chunks


# =============================================================================
# 메인 파서
# =============================================================================

def parse_file(filepath: Path) -> list[CodeChunk]:
    """파일 확장자에 따라 적절한 파서로 청킹"""
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError, FileNotFoundError) as e:
        print(f"파일 읽기 실패: {filepath} - {e}")
        return []

    if not content.strip():
        return []

    extension = filepath.suffix.lower()
    language = EXTENSION_TO_LANGUAGE.get(extension, "unknown")

    if extension == ".py":
        return parse_python(filepath, content)
    elif extension == ".java":
        return parse_java(filepath, content)
    elif extension == ".vue":
        return parse_vue(filepath, content)
    elif extension == ".js":
        return parse_javascript(filepath, content)
    else:
        # 지원하지 않는 확장자
        return []


def parse_codebase(base_path: str = CODE_BASE_PATH) -> list[CodeChunk]:
    """전체 코드베이스를 스캔하고 청킹"""
    files = scan_files(base_path)
    print(f"스캔된 파일 수: {len(files)}")

    all_chunks = []
    for filepath in files:
        chunks = parse_file(filepath)
        all_chunks.extend(chunks)
        if chunks:
            print(f"  {filepath.name}: {len(chunks)} 청크")

    print(f"총 청크 수: {len(all_chunks)}")
    return all_chunks


# =============================================================================
# 테스트
# =============================================================================

if __name__ == "__main__":
    # 테스트 실행
    chunks = parse_codebase()

    # 프로젝트별 통계
    from collections import Counter
    projects = Counter(c.project for c in chunks)
    languages = Counter(c.language for c in chunks)
    chunk_types = Counter(c.chunk_type for c in chunks)

    print("\n=== 프로젝트별 청크 수 ===")
    for project, count in projects.most_common():
        print(f"  {project}: {count}")

    print("\n=== 언어별 청크 수 ===")
    for lang, count in languages.most_common():
        print(f"  {lang}: {count}")

    print("\n=== 타입별 청크 수 ===")
    for ctype, count in chunk_types.most_common():
        print(f"  {ctype}: {count}")
