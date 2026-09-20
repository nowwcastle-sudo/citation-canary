# Citation Canary — 실험 단계 오픈소스

[English](https://github.com/nowwcastle-sudo/citation-canary/blob/main/README.md) · [한국어](https://github.com/nowwcastle-sudo/citation-canary/blob/main/README.ko.md)

Citation Canary는 내 컴퓨터의 HWPX 문서에서 법령·행정규칙 인용 후보를 찾아,
사용자가 준비한 날짜별 출처 목록(카탈로그)과 대조합니다. 원본을 고치거나
네트워크에 접속하지 않고, 사람이 검토할 JSON 보고서를 만듭니다.
현재는 실험 단계 오픈소스이며 법적 정확성, 사건·판례의 진위, 실제 사용자의
지속적인 활용은 검증되지 않았습니다.

인용을 직접 확인하기 전에 검토할 항목을 모으는 데 쓸 수 있습니다. `--demo`는
가상의 입력 파일을 만들고, 실제 스캔은 입력 파일을 읽어 화면이나 지정한 파일에
보고서를 출력합니다.

라이선스는 Apache License 2.0입니다. [`LICENSE`](LICENSE)를 참고하세요.

## 어떤 일을 하나요

| 단계 | 입력과 처리 | 결과 또는 범위 |
| --- | --- | --- |
| 읽기 | HWPX ZIP/XML 문서 한 개와 로컬 카탈로그 한 개 | 섹션의 텍스트 노드를 수집합니다. HWP·PDF·DOCX·이미지/OCR 입력은 지원하지 않습니다. |
| 찾기 | 카탈로그에 등록된 정확한 제목 | 같은 텍스트 노드에서 제목 뒤 32자 이내, 다음 제목 전에 처음 나오는 `제N조` 또는 `제N조의N`을 연결합니다. |
| 대조 | 명시한 기준일과 카탈로그의 버전별 적용 기간 | 사유와 함께 `CURRENT`, `HISTORY`, `REVIEW`, `UNKNOWN` 중 하나를 부여합니다. |
| 보고 | 후보 위치, 카탈로그 근거, 원본 해시 | 사람이 검토할 JSON을 만듭니다. 문서를 자동 수정하지 않습니다. |

여러 텍스트 노드에 나뉜 제목, 다른 표기, 항·호의 세부 의미는 이 대조 규칙의
범위 밖입니다. 등록된 제목과 겹치지 않는 `법`, `규정`, `고시`, `훈령`, `예규`
표현은 모호한 후보로 잡힐 수 있고 지원하지 않는 인용은 후보로 잡히지 않을
수도 있습니다. 보고서를 반환하기 직전에 원본 해시를 다시 확인하며,
원본이 바뀌었으면 `SOURCE_CHANGED_DURING_SCAN` 오류와 빈 근거 항목을 반환합니다.

## 실험판 내려받기

[v0.2.0-experimental.1 릴리스](https://github.com/nowwcastle-sudo/citation-canary/releases/tag/v0.2.0-experimental.1)에서
다음 두 파일을 모두 내려받으세요. 공개 다운로드에는 GitHub 계정이나 토큰이 필요 없습니다.

- [citation-canary-0.2.0.pyz](https://github.com/nowwcastle-sudo/citation-canary/releases/download/v0.2.0-experimental.1/citation-canary-0.2.0.pyz)
- [citation-canary-0.2.0.pyz.sha256](https://github.com/nowwcastle-sudo/citation-canary/releases/download/v0.2.0-experimental.1/citation-canary-0.2.0.pyz.sha256)

새 폴더에 두 파일을 저장하세요. 하나라도 다운로드에 실패하면 멈추고, 실패한
파일은 보존한 채 다른 새 폴더에서 다시 받으세요. 다른 릴리스의 체크섬으로
대체하면 안 됩니다. SHA-256은 파일 바이트의 일치 여부를 확인하며, 배포자의
신원을 인증하지 않습니다. 다운로드 후 프로그램 자체는 오프라인으로 실행됩니다.

소스에서 빌드하려면 [소스 빌드 안내](docs/release/public-candidate.md)를 보세요.
고정된 `v0.2.0-experimental.1` 배포 아카이브에는 Apache 라이선스를 포함해
정확히 11개 항목이 들어갑니다. 현재 소스에서 빌드한 후보는 아래 설명처럼
구성이 다릅니다.

`v0.2.0-experimental.1` 태그와 배포 파일은 고정되어 있습니다. 저장소 `main`의
문서는 해당 릴리스 태그의 README보다 최신일 수 있습니다. `README.ko.md`는 저장소에서
제공하는 번역이며 zipapp에 추가된 항목이 아닙니다. 내려받은 릴리스의 정확한
구성을 확인할 때는 해당 태그의 문서를 보세요.

## 로컬 검토 후보 (소스 빌드, 기존 릴리스와 별개)

현재 소스에는 사람의 처분 기록, 보수적인 보고서 비교, 오프라인 HTML 열람이
추가되었습니다. 위 `v0.2.0-experimental.1` 다운로드에는 이 명령이 없습니다.
소스에서 만든 로컬 후보의 아카이브 항목은 정확히 15개이며, 기존 릴리스의
11개와 구별해야 합니다. 새 릴리스가 발행됐다는 뜻은 아닙니다. 저장소 루트에서
PowerShell을 열고, 아래 결과 이름이 아직 사용되지 않았는지 확인한 뒤 한 줄씩
실행하세요.

```powershell
python .\tools\build_zipapp.py --source .\src --output .\local-review-candidate.pyz
python .\local-review-candidate.pyz --demo .\local-review-demo
python .\local-review-candidate.pyz --document .\local-review-demo\synthetic-review.hwpx --as-of 2024-12-31 --catalog .\local-review-demo\catalog.json --output .\local-review-report.json
python .\local-review-candidate.pyz review --report .\local-review-report.json --ledger .\local-review-ledger.json --action decide --item 1 --disposition investigate
python .\local-review-candidate.pyz render --report .\local-review-report.json --ledger .\local-review-ledger.json --output .\local-review.html
python .\local-review-candidate.pyz compare --before .\local-review-report.json --after .\local-review-report.json
```

같은 보고서 두 개를 비교하는 마지막 명령은 기능 확인용이며, 변경된 문서를
검토했다는 증거가 아닙니다. 해시가 다른 보고서는 관계를 사용자가 확인한
경우에만 `--related-versions`를 붙이세요. 대응은 후보로 남고 처분은 자동으로
옮겨지지 않습니다. 보고서·처분 기록·HTML에는 민감한 인용 식별자가 있을 수
있으니 로컬에 보관하고 공개 이슈에 첨부하지 마세요. 자세한 절차와 실패 시
조치는 [로컬 검토 안내](docs/local-review.md), 실행 증거는
[로컬 검증 표](docs/local-completion-verification.md)를 보세요.

## 실행 조건과 주의 범위

- Python 3.11 이상이 필요합니다. `.pyz`는 Python zipapp 형식이며 패키지를 따로 설치하지 않습니다.
- 스캔하려면 로컬 HWPX, 명시적인 `--as-of` 기준일, 로컬 UTF-8 카탈로그가 필요하며 카탈로그는 스키마 버전 `"1"`을 따라야 합니다.
- 실제 공식 출처 카탈로그는 포함되어 있지 않으며 프로그램이 갱신하지도 않습니다. `--demo`는 가상의 학습용 입력만 만듭니다. 실제 검토 전에는 사용자가 출처와 최신성을 확인해야 합니다.
- 원본 문서는 로컬에 남습니다. 프로그램은 네트워크 요청·업로드·텔레메트리·인증 요청·업데이트 확인을 하지 않습니다.
- HWPX를 편집하거나 자동 교정하지 않습니다. 상태값은 적법성·준수 여부·유효성·수정 의무에 대한 판정이 아닙니다.

## 파일 검증과 실행 준비

터미널과 Python 3.11 이상을 준비하세요. Windows에서는 다운로드 폴더에서
PowerShell을 여세요. `python` 명령을 찾을 수 없다면
[python.org](https://www.python.org/downloads/)에서 Python을 설치한 뒤 PowerShell을
다시 열어 버전을 확인하세요. 스캐너 실행에 한컴오피스나 API 키는 필요 없습니다.
아래 명령은 Windows PowerShell 경로를 사용합니다.

[v0.2.0-experimental.1 사전 릴리스](https://github.com/nowwcastle-sudo/citation-canary/releases/tag/v0.2.0-experimental.1)의
`citation-canary-0.2.0.pyz`와 `citation-canary-0.2.0.pyz.sha256`을 같은 폴더에 두고,
그 폴더의 PowerShell에서 다음 명령을 한 줄씩 순서대로 실행하세요.

```powershell
$checksumText=Get-Content -Raw -LiteralPath '.\citation-canary-0.2.0.pyz.sha256'
if ([string]::IsNullOrWhiteSpace($checksumText)) { throw 'Checksum file is empty.' }
$expected=$checksumText.Split("`n")[0].Split('  ')[0]
$actual=(Get-FileHash -LiteralPath '.\citation-canary-0.2.0.pyz' -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -cne $expected) { throw 'Checksum mismatch. Do not run this artifact.' }
python --version
python .\citation-canary-0.2.0.pyz --help
```

체크섬이 다르면 이후 명령을 실행하지 마세요. `python --version`은 3.11 이상이어야
합니다. 공개 다운로드에는 인증이 필요 없으며 프로그램 자체에도 인증 기능이 없습니다.

## 첫 실행: 데모 생성 후 스캔

검증한 pyz 파일이 있는 폴더에서 실행하세요. `citation-demo` 폴더는 아직 없어야
합니다. 이 명령은 가상의 학습용 입력을 만들며 스캔은 수행하지 않습니다.

```powershell
python .\citation-canary-0.2.0.pyz --demo .\citation-demo
$LASTEXITCODE
```

예상 결과는 종료 코드 `0`과 `notice: SYNTHETIC_DEMO_ONLY`가 포함된 생성 목록입니다.
새 폴더에 `synthetic-review.hwpx`, `catalog.json`, `README.txt` 세 파일만 생성됩니다.
모든 출처 URL은 `example.invalid`이며 제목·시행일·조회 정보도 가상입니다.
HWPX는 스캐너용 최소 예제로, 편집용 한컴 서식이나 실제 기관 문서가 아닙니다.

데모 생성 시 작은 JSON 안내가 표준 출력(stdout, 터미널 출력)에 나타납니다.
이것은 스캔 보고서가 아니며 스캔 보고서는 `--output`을 생략했을 때만 표준
출력으로 나옵니다. 지원을 위해 파일을 남길 때는 아래처럼 UTF-8 `--output`을 쓰세요.

기존 폴더는 비어 있어도 거부합니다. 이전 파일이나 일부만 생성된 파일은 보존하고
다른 새 폴더를 선택하세요. 상위 폴더가 없거나 경로에 `..`가 있거나 확인된
심볼릭 링크·재분석 경로가 있으면 거부합니다. `--demo`와 스캔 옵션은 함께 쓸 수 없습니다.

생성된 두 입력을 가상의 고정 기준일 `2024-12-31`로 스캔하세요.

```powershell
python .\citation-canary-0.2.0.pyz --document .\citation-demo\synthetic-review.hwpx --as-of 2024-12-31 --catalog .\citation-demo\catalog.json
$LASTEXITCODE
```

예상 결과는 종료 코드 `0`, `collection_errors: []`, 그리고 순서대로
`CURRENT`, `HISTORY`, `REVIEW`, `UNKNOWN`인 네 항목입니다. 사유는 각각
`EXACT_CURRENT_MATCH`, `EXACT_HISTORICAL_MATCH`, `PROVISION_MISMATCH`,
`AMBIGUOUS_CITATION`입니다. 정상 실행 결과에도 `REVIEW`나 `UNKNOWN`이 있을 수 있습니다.

같은 보고서를 별도 UTF-8 파일에 저장하려면 다음과 같이 실행하세요.

```powershell
python .\citation-canary-0.2.0.pyz --document .\citation-demo\synthetic-review.hwpx --as-of 2024-12-31 --catalog .\citation-demo\catalog.json --output .\citation-report.json
$LASTEXITCODE
Get-Content -Raw -Encoding UTF8 -LiteralPath '.\citation-report.json'
```

예상 결과는 종료 코드 `0`이며, 스캔 중 표준 출력에는 보고서가 나오지 않고 지정한
파일에 UTF-8 JSON이 저장됩니다. 기존 보고서를 보존하려면 새 파일명을 쓰세요.
지정한 출력 파일이 이미 있으면 원자적으로 교체합니다. HWPX와 카탈로그 경로는
출력 대상으로 지정할 수 없습니다. Windows PowerShell 5.1은 외부 프로그램의
표준 출력을 다른 인코딩으로 읽거나 저장할 수 있으므로 `--output`으로 저장하고
`-Encoding UTF8`을 명시해 읽으세요.

[카탈로그 스키마 v1 안내](docs/catalog-schema-v1.md)에는 모든 필드, 데모와 동일한
가상 예제, 생성·저장·검토 절차가 있습니다. UTF-8 BOM 없이 저장하세요. 실제 공식
출처인지, 연혁이 이어지는지, 접근이 허용되는지, 최신인지는 사람이 확인해야 합니다.
프로그램은 URL 문법만 검사하고 출처를 내려받지 않습니다.

추출은 카탈로그에 있는 제목을 출발점으로 삼으며 XML 텍스트 노드별로 좁은 조문
규칙을 적용합니다. 후보가 0개라고 해서 전체 검토를 마친 것도, 문서에 인용·법적
문제가 없는 것도 아닙니다.

스캔 옵션은 다음과 같습니다. 필수 조건은 `--demo`를 쓰지 않을 때 적용됩니다.

| 옵션 | 용도 |
| --- | --- |
| `--document` | 필수. 로컬 `.hwpx` 입력 한 개 |
| `--as-of` | 필수. 정확한 `YYYY-MM-DD` 형식의 기준일 |
| `--catalog` | 필수. 로컬 UTF-8 스키마 v1 카탈로그 JSON 한 개 |
| `--output` | 선택. 별도 JSON 보고서 경로. 생략하면 표준 출력으로 내보냅니다. 문서·카탈로그 경로와 달라야 합니다. |
| `-h` / `--help` | 옵션 목록 표시 |
| `--demo NEW_DIRECTORY` | 가상 입력 생성. 모든 스캔 옵션과 함께 사용할 수 없습니다. |

원본 HWPX를 그대로 보존하고 보고서는 별도로 저장하세요.

## 실제 문서 스캔

[스키마 안내](docs/catalog-schema-v1.md)에 따라 별도 카탈로그를 준비하세요.
프로그램 밖에서 공식 출처를 확인한 뒤 정확한 제목, 조문 표기, 고정 조문 ID,
버전별 적용 기간, HTTPS 출처 URL, 조회 시각을 입력합니다. 최상위 필드는 문자열
`"1"`인 `schema_version`과 비어 있지 않은 `records` 배열입니다. 각 기록에는
`record_id`, `official_source`, `versions`가 들어갑니다. 안내 문서에 하위 필드와
완전한 예제가 있습니다. 추가 필드와 중복 JSON 키는 거부합니다.

적용 기간은 `effective_from`을 포함하고 `effective_to`를 제외합니다. 버전은
순서대로 나열하고 서로 겹치지 않아야 하며 마지막 버전은 `effective_to: null`이어야
합니다. 사람이 동일 조문이 이어진다고 확인한 경우에만 버전 간 `canonical_id`를
같게 쓰세요. UTF-8 BOM 없이 저장하세요. 프로그램은 공식 출처의 권위, 조문의
연속성, 최신성을 확인하지 않습니다. 데모 카탈로그는 실제 문서의 근거로 쓸 수 없습니다.

검토할 문서를 `review-input.hwpx`, 별도로 준비한 카탈로그를 `review-catalog.json`이라는
이름으로 검증한 zipapp 폴더에 두세요. 원본 사본을 보존하세요. 같은 폴더에서
아래 명령을 실행하면 기준일을 직접 입력하게 됩니다. 다시 실행할 때는 아직 쓰지
않은 보고서 파일명을 선택하세요.

```powershell
$reviewDate=Read-Host 'Review date (YYYY-MM-DD)'
python .\citation-canary-0.2.0.pyz --document .\review-input.hwpx --as-of $reviewDate --catalog .\review-catalog.json --output .\review-report.json
$LASTEXITCODE
Get-Content -Raw -Encoding UTF8 -LiteralPath '.\review-report.json'
```

저장된 보고서를 읽기 전에 종료 코드를 확인하세요. 실행에 실패하면 같은 경로에
이전 보고서가 남아 있을 수 있습니다. `as_of`, `document_sha256`, `catalog_sha256`을
대조하고 `collection_errors`를 확인한 뒤 항목을 검토하세요. 어떤 기준일을 써야
하는지는 스캐너가 정하지 않습니다.

현재 소스에는 [구조·인용 처리 한도](docs/runtime-resource-limits.md)가 적용됩니다.
크거나 반복이 많은 입력은 `HWPX_LIMIT_EXCEEDED` 또는 `REFERENCE_LIMIT_EXCEEDED`로
실패하며 일부 근거만 담은 보고서를 반환하지 않습니다. 정상적인 대용량 문서도
거부될 수 있으며 이것은 법적 판정이 아닙니다. 검토한 작은 카탈로그를 쓰고,
원본을 보존한 채 별도 범위를 정해 검토하세요.

압축 입력은 100 MiB, 아카이브 항목은 10,000개, 섹션 하나는 20 MiB, 전체 압축 해제
항목은 200 MiB까지 허용합니다. 전체 섹션을 합쳐 XML 요소는 200,000개, 텍스트 요소는
100,000개, 보존할 문자는 20 × 1,024 × 1,024자까지입니다. 중첩 깊이는 128,
섹션 번호 접미사는 32자리까지입니다. 인용 추출은 텍스트 노드별·문서 전체 각각
100,000회 일치 조사와 10,000개 후보를 허용합니다. 별도로 공급한 카탈로그의
로딩·대조에는 이 한도가 적용되지 않으며 실행 시간이나 최대 메모리를 보장하지
않습니다. 집계 방식과 해당 소스의 세부 내용은 연결된 안내를 보세요.

## 보고서 읽기와 종료 코드

문서 이름은 SHA에서 만든 가명 `document-<12hex>.hwpx`로 표시하고, 문서와 카탈로그의
전체 SHA-256도 기록합니다. 보고서에는 원본 HWPX 문단이나 원래 파일명 대신 위치와
카탈로그 근거가 들어갑니다. 수집 정보를 줄인 것이며 익명화가 아닙니다.
HWPX·보고서 본문·카탈로그·비밀값·로컬 경로를 이슈에 첨부하지 마세요.

각 항목은 다음 상태 중 하나를 갖습니다.

| 상태 | 의미 |
| --- | --- |
| `CURRENT` | 좁은 카탈로그 식별·조문 대조에서 `--as-of` 기준과 맞습니다. 법적 결론은 아닙니다. |
| `HISTORY` | 이전 적용 버전과 일치하고 이후 카탈로그의 변경이 표시됩니다. 자동으로 오류가 되는 것은 아닙니다. |
| `REVIEW` | 근거 충돌·불일치·날짜 조건 때문에 사람이 살펴봐야 합니다. 무효라는 뜻은 아닙니다. |
| `UNKNOWN` | 카탈로그 근거가 부족하거나 모호합니다. 보고서에 사유가 나옵니다. |

| 상태 | 다음 검토 |
| --- | --- |
| `CURRENT` | 명시한 날짜의 근거를 보존하고 필요한 사람의 검토를 마칩니다. |
| `HISTORY` | 문구를 고칠지 정하기 전에 기준일과 이후 변경을 비교합니다. |
| `REVIEW` | 출처와 문서 문맥을 직접 확인하고 검토자의 처분을 별도로 기록합니다. |
| `UNKNOWN` | 더 나은 카탈로그 근거나 명확한 인용 문맥을 확보합니다. 안전 판정이나 자동 수정으로 해석하지 않습니다. |

수집 오류는 상태값과 별개이며, 오류가 있으면 근거를 확보한 것으로 처리하지 않습니다.

| 상황 | 종료 코드 |
| --- | ---: |
| 수집 오류 없이 스캔 성공 | `0` |
| 수집 오류가 있는 스캔 결과 | `1` |
| 예상하지 못한 실행·출력 오류 | `1` |
| 인수·요청 오류, 잘못된 날짜·카탈로그 포함 | `2` |
| 안전한 상대 파일명 목록과 함께 데모 생성 성공 | `0` |
| 잘못되거나 재사용한 데모 폴더: `DEMO_DESTINATION_INVALID` | `2` |
| 데모 생성 입출력 실패: `DEMO_CREATE_FAILED`; 일부 파일 보존 | `1` |

오류 안내는 표준 오류(stderr)에 안전한 문구로 출력됩니다. 상세 예외 추적이나
사용자의 실제 로컬 경로는 표시하지 않습니다.

`Contents/section0.xml:t[2]` 같은 `locator`는 XML 텍스트 노드 위치이며 페이지
번호가 아닙니다. `reference`는 발견한 제목·조문을, `evidence`는 카탈로그 출처,
조회 시각, 일치한 적용 기간을 담습니다. 연혁 항목에는 `version_transition`이
있을 수 있습니다. 사유와 근거를 확인한 뒤 검토자의 처분을 기록하세요. 이후 문서
수정이 자동으로 실행되지는 않습니다.

보고서 최상위 필드는 `schema_version`, `document_name`, `document_sha256`, `as_of`,
`catalog_sha256`, `items`, `collection_errors`입니다. 각 항목에는 `locator`,
`reference`, `status`, `reason_code`, `evidence`가 있습니다. 수집 오류에는 `code`,
`stage`, `fatal`, `locator`, `message`가 있습니다. 먼저 수집 오류를 보세요.
치명적 오류 뒤의 빈 `items` 배열은 스캔이 근거를 제공하지 못했다는 뜻입니다.

## 문제 해결

| 증상 또는 메시지 | 확인할 사항 |
| --- | --- |
| 체크섬 불일치 | 실행을 멈추고 파일을 보존하세요. 새 폴더에 같은 릴리스의 두 파일을 다시 받으세요. |
| `ARGUMENT_ERROR` | 필수 스캔 입력 세 개를 모두 지정하거나 `--demo`만 쓰세요. 옵션 축약은 허용하지 않습니다. |
| `Invalid --as-of date. Expected YYYY-MM-DD.` | 실제 달력에 있는 날짜를 정확한 형식으로 입력하세요. |
| `Document file was not found.` / `Catalog file was not found.` | 현재 폴더와 실제 파일명을 확인하세요. 공백이 있는 경로는 따옴표로 감싸세요. |
| `Catalog is not valid UTF-8 JSON.` | UTF-8 BOM 없음, JSON 문법, 중복 키를 확인하세요. |
| `Catalog does not conform to schema version 1.` | 스키마 안내와 필드·날짜·기간·URL·시각·고유 ID를 대조하세요. |
| `DEMO_DESTINATION_INVALID` | 존재하는 상위 폴더 아래 새 폴더를 선택하세요. 이전·부분 생성 파일은 보존하세요. |
| `DEMO_CREATE_FAILED` | 쓰기 권한과 저장 공간을 확인하세요. 부분 생성 파일은 남습니다. 새 폴더로 다시 시도하세요. |
| `HWPX_LIMIT_EXCEEDED` / `REFERENCE_LIMIT_EXCEEDED` | 원본을 보존하고 별도 범위를 정해 검토하세요. 빈 항목을 이상 없음으로 해석하지 마세요. |
| `SOURCE_CHANGED_DURING_SCAN` | 동시에 편집하지 말고 내용이 고정된 로컬 사본을 스캔하세요. |
| `UNEXPECTED_ERROR` | 출력 상위 폴더, 쓰기 권한, 저장 공간을 확인하고 안전한 오류 문구와 종료 코드를 기록하세요. |
| 종료 코드 `0`인데 `REVIEW`·`UNKNOWN`이 있거나 항목이 없음 | 사유와 추출 범위를 확인하세요. `0`은 실행 결과이며 법적 정확성을 뜻하지 않습니다. |

## 지원과 릴리스의 한계

[GitHub Issues](https://github.com/nowwcastle-sudo/citation-canary/issues)에는 가상 입력으로
재현한 오류와 민감하지 않은 버그 정보를 올리세요. 릴리스 태그, Python 버전, 명령
형식, 종료 코드, 고정 오류 코드·문구를 포함하세요. 실제 HWPX, 보고서 본문,
카탈로그, 로컬 경로, 원본 해시는 공개하지 마세요. 가명과 해시도 문서를 원본과
연결하는 단서가 될 수 있습니다. 비공개 취약점 제보는 [SECURITY.md](SECURITY.md)를 보세요.

저장소는 Apache License 2.0으로 배포하며 zipapp에는 변경하지 않은
[LICENSE](LICENSE)가 들어 있습니다. 릴리스 책임자는 `nowwcastle-sudo`입니다.
지원 SLA, 법적 정확성 보증, 사건·판례 진위 보증, 입증된 실제 사용자 채택 주장은
없습니다. 가상 데모를 실행했다는 사실로 반복 사용·조달·법적 정확성을 입증할 수 없습니다.

[Windows 호환성 안내](docs/compatibility/windows.md)에서 CI 검증 범위를 확인하세요.
참여하기 전 [CONTRIBUTING.md](CONTRIBUTING.md)와
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)를 읽어 주세요.
[소스 빌드 안내](docs/release/public-candidate.md)에는 업데이트와 롤백 절차도 있습니다.
소프트웨어가 공개되어 있다는 사실이 민감한 문서의 호스팅 처리를 승인하지는 않습니다.
