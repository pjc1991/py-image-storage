# Legacy Files

이 디렉토리는 관심의 분리 리팩토링 이전의 파일들을 보관합니다.
This directory contains files from before the Separation of Concerns refactoring.

## 파일 매핑 (File Mapping)

### 기존 파일 → 새 파일
- `observer.py` → `application.py` + `main.py`
- `file_handler.py` → `processor.py` + `watcher.py`
- `image_handler.py` → `compressor.py`
- `task_handler.py` → *(새 아키텍처는 asyncio 기본 사용)*

## 왜 보관하나요? (Why Keep These?)

1. **참조용**: 기존 로직 확인이 필요할 때
2. **롤백용**: 문제 발생 시 되돌릴 수 있음
3. **비교용**: 리팩토링 전후 비교

## 삭제해도 되나요? (Can I Delete?)

네, 새 아키텍처가 안정적으로 작동하면 삭제해도 됩니다.
Yes, you can delete these once the new architecture is stable.

## 날짜 (Date)

보관 날짜: 2025-01-27
