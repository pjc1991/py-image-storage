# Tests

새 아키텍처를 위한 테스트입니다.
Tests for the new architecture.

## 테스트 파일 (Test Files)

### test_config.py
설정 관리 테스트
- 환경 변수 로딩
- 기본값 처리
- 유효성 검사

### test_compressor.py
이미지 압축 테스트
- JPEG/PNG → WebP 변환
- 이미지 리사이징
- 압축 캐싱
- 파일 크기 임계값

### test_processor.py
파일 처리 테스트
- 파일 처리 워크플로우
- 배치 처리
- WebP 파일 처리
- 에러 처리

## 테스트 실행 (Running Tests)

### 모든 테스트 실행
```bash
pytest tests/ -v
```

### 특정 테스트만 실행
```bash
pytest tests/test_config.py -v
pytest tests/test_compressor.py -v
pytest tests/test_processor.py -v
```

### 커버리지 포함
```bash
pytest tests/ --cov=. --cov-report=html
```

## 필요한 패키지 (Requirements)

테스트를 실행하려면 다음 패키지가 필요합니다:

```bash
pip install pytest pytest-asyncio pytest-cov
```

## 구 테스트 (Old Tests)

기존 아키텍처의 테스트는 `../legacy/` 디렉토리로 이동했습니다.
- test_asyncio_import_fix.py
- test_handle_file_repro.py
- test_initial_file_handle.py
- test_multiprocessing.py
- test_multiprocessing_asyncio_fix.py

## 테스트 커버리지 목표 (Coverage Goals)

- Config: 100%
- ImageCompressor: >90%
- FileProcessor: >85%
- Integration: >80%

## 테스트 작성 가이드 (Writing Tests)

### 픽스처 사용 (Using Fixtures)

```python
@pytest.fixture
def config(self, tmp_path):
    # 테스트용 설정 생성
    pass

@pytest.fixture
def mock_compressor(self):
    # Mock 객체 생성
    pass
```

### 비동기 테스트 (Async Tests)

```python
@pytest.mark.asyncio
async def test_something_async(self):
    result = await some_async_function()
    assert result is True
```

### 임시 파일 (Temporary Files)

```python
def test_with_file(self, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    # ...
```

## CI/CD

GitHub Actions나 다른 CI 시스템에서 자동으로 테스트를 실행할 수 있습니다:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-asyncio
      - run: pytest tests/ -v
```
