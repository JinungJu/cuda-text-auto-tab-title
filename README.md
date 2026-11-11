# Auto Tab Title

CudaText에서 미저장 메모의 내용을 탭 제목으로 표시합니다. 예를 들어 첫 줄이 `# Mac mini SSH 설정`이면 입력을 잠시 멈춘 뒤 탭 제목이 `Mac mini SSH 설정`으로 바뀝니다. 파일로 처음 저장하면 CudaText가 실제 파일명으로 제목을 바꿉니다.

## 설치

1. Windows용 CudaText 1.236.0 이상(Python API 1.0.483 이상)을 사용합니다. CudaText에 포함된 Python과 표준 라이브러리만 사용합니다.
2. CudaText에서 **File → Open**(`Ctrl+O`)으로 `plugin.Auto_Tab_Title.zip`을 그대로 열고 설치를 승인합니다.
3. CudaText를 재시작합니다. 새 탭에 첫 줄을 입력한 뒤 잠시 기다려 제목이 바뀌는지 확인합니다.

## 사용

- **자동 이름**은 앞에서부터 기본 10줄 중 처음으로 제목을 만들 수 있는 줄을 사용합니다. 앞뒤 공백을 제거하고 연속 공백을 하나로 정리합니다. Markdown의 `#`부터 `######`까지, 공백 또는 줄 끝이 뒤따르는 제목 기호를 제거합니다. 닫는 제목 기호도 처리하며 `#태그`와 같은 해시태그는 유지합니다.
- **Plugins → Auto Tab Title → Rename Current Tab**을 선택하면 현재 제목이 입력란에 표시됩니다. 새 제목을 입력하면 해당 탭이 수동 모드가 됩니다. 취소하거나 공백만 입력하면 제목이 그대로 유지됩니다.
- **Reset Tab Title to Auto**를 선택하면 수동 모드가 해제되고, 현재 본문으로 즉시 제목을 만듭니다. 사용할 줄이 없으면 CudaText가 기본 제목을 다시 부여합니다. 이때 `Untitled` 뒤의 번호가 처음과 달라질 수 있습니다.
- **단축키 설정**은 `F1`로 명령 팔레트를 열어 `Rename Current Tab`을 검색한 뒤 `F9`를 누릅니다. 권장 키는 `Ctrl+Shift+R`입니다. 해당 키가 다른 명령에 할당되어 있으면 CudaText가 기존 명령을 알려 줍니다. 기존 할당을 유지하려면 덮어쓰기를 취소하고 다른 키를 선택합니다. [CudaText 명령 팔레트 문서](https://wiki.freepascal.org/CudaText#Command_Palette)

## 설정

설치된 `py/cuda_auto_tab_title/settings.example.json`을 CudaText의 실제 설정 폴더에 `cuda_auto_tab_title.json`이라는 이름으로 복사합니다. CudaText에서 **Options → Settings - user**를 열면 사용자 설정 파일이 있는 폴더를 확인할 수 있습니다. JSON을 편집한 뒤 재시작합니다. 파일이 없거나 항목이 누락·손상된 경우 기본값을 사용합니다.

| 항목 | 기본값 | 동작 |
| --- | --- | --- |
| `enabled` | `true` | 자동 갱신과 수동 이름 명령을 활성화합니다. |
| `auto_rename` | `true` | 입력이 멈췄을 때, 탭을 전환했을 때, 세션을 복원했을 때 제목을 자동 갱신합니다. `false`여도 수동 이름과 명시적 리셋 명령을 사용할 수 있습니다. |
| `max_title_length` | `28` | 자동 제목의 최대 길이입니다. 유니코드 코드 포인트 기준 1~4096이며 말줄임표 `…`를 길이에 포함합니다. |
| `scan_lines` | `10` | 탐색할 앞부분의 최대 줄 수입니다. 1~1000을 지정할 수 있습니다. |
| `strip_markdown` | `true` | Markdown 제목 기호를 제거합니다. |
| `rename_saved_files` | `false` | 이 버전에서는 항상 `false`로 동작합니다. |

## 세션 복원

CudaText의 `ui_reopen_session`을 켜고 종료 시 세션에 메모를 보관합니다. CudaText가 본문, 제목과 탭 ID를 복원합니다. 플러그인은 설정 폴더의 `cuda_auto_tab_title_state.json`에 탭 ID, 제목의 해시, 선행 별표 개수, 자동·수동 모드만 기록합니다. 앱이 실제로 복원한 탭에서 ID, 제목 해시, 제목 사유가 일치할 때만 모드를 되살립니다. 닫힌 탭은 메모리에서 정리하며, 다른 세션이나 세션 백업에 남아 있을 수 있는 탭의 메타데이터는 최근 4096개까지 유지합니다. [CudaText 세션 문서](https://wiki.freepascal.org/CudaText#Sessions), [세션 저장·복원 소스](https://github.com/Alexey-T/CudaText/blob/master/app/formmain_loadsave.inc)

- CudaText가 세션에서 제외한 탭이나 본문은 복원할 수 없습니다. 상태 파일이 누락되었거나 세션 제목과 일치하지 않으면 복원된 사용자 지정 제목을 보존합니다. 자동 갱신을 되살리려면 해당 메모를 새 미저장 탭으로 옮길 수 있습니다.
- API는 사용자 지정 제목을 설정한 플러그인의 이름을 제공하지 않습니다. 다른 플러그인이 제목을 바꾼 이벤트를 받으면 소유권을 해제합니다. 다른 플러그인이 같은 제목을 다시 설정해 변경 이벤트가 발생하지 않으면 이를 구별할 수 없습니다.
- 같은 탭의 과거 세션 백업에 현재와 다른 제목이 들어 있으면 그 백업의 자동·수동 모드를 복원하지 못할 수 있습니다. 여러 CudaText 인스턴스가 같은 설정 폴더에 동시에 세션을 저장하는 경우에도 모드 복원을 보장할 수 없습니다.

## 적용 범위

파일 경로가 없는 일반 텍스트 탭을 대상으로 합니다. CudaText 특수 탭, 뷰어, 서로 다른 문서를 담는 분할 탭, 다른 플러그인이 설정한 제목은 건너뜁니다. 제목 변경에는 탭 제목 속성만 사용합니다. 첫 저장 시 CudaText가 파일명을 표시한 뒤 플러그인이 해당 탭의 모드를 정리합니다. [제목 속성 구현](https://github.com/Alexey-T/CudaText/blob/master/app/formmain_py_api.inc), [파일 저장 구현](https://github.com/Alexey-T/CudaText/blob/master/app/form_frame.pas)

본문은 `on_change_slow`와 탭 전환, 세션 복원·저장 시점에 검사합니다. `on_tab_add`는 본문이 로드되기 전에 호출되므로, 새 빈 탭은 그대로 두고 입력 후 갱신합니다. 성능을 위해 앞부분의 지정된 줄만 읽으며, 64 KiB를 초과하는 개별 줄은 건너뜁니다. [CudaText Python API](https://github.com/Alexey-T/CudaText/blob/master/wiki/cudatext_api.wiki)

## 삭제

1. 기존 미저장 탭의 제목도 기본값으로 되돌리려면 **Plugins → Auto Tab Title → Restore Default Titles (Before Uninstall)**을 실행합니다. 이 명령은 플러그인이 관리하는 제목을 지우고 현재 실행 중에는 자동 갱신을 일시 중지합니다.
2. **Plugins → Addons Manager → Remove add-on…**에서 **Auto Tab Title**을 제거하고 CudaText를 재시작합니다. 메뉴에서 제거할 수 없으면 CudaText를 종료한 뒤 `py/cuda_auto_tab_title` 폴더를 삭제합니다.
3. 설정 폴더의 `cuda_auto_tab_title.json`과 `cuda_auto_tab_title_state.json`은 필요에 따라 삭제할 수 있습니다. 메모 본문을 보관하는 `.cuda-session` 파일은 그대로 두십시오.

## 소스 및 테스트

소스는 `cuda_auto_tab_title/`에 있으며 설치 ZIP 안에도 같은 모듈이 들어 있습니다. `tests/`가 있는 폴더에서 다음 명령으로 Python 3.8 이상에서 테스트를 실행할 수 있습니다.

```powershell
python -B -m unittest discover -s tests -v
```

모의 API 테스트 19개를 통과했습니다. 제목 추출과 길이 제한, 수동 모드, 저장 파일과 특수 탭 보호, 세션 소유권 확인, 닫힌 탭 상태 정리와 설정 기본값을 검증합니다.

격리한 Windows용 **CudaText 1.237.2.0 (API 1.0.485)**에서도 다음을 확인했습니다.

- CudaText의 ZIP 설치 API를 통한 설치, 빈 탭의 기본 제목, 입력·수정·삭제 후 자동 갱신, 탭별 독립 동작
- 실제 이름 변경 대화상자의 현재 제목 표시와 한글 수동 이름 입력, 자동 모드 복원, 본문이 비었을 때 기본 제목 복원
- 앱 종료 후 재시작 시 탭 ID와 자동·수동 제목 및 모드 복원, 다른 플러그인 제목 보호
- 실제 Save As 대화상자의 기본 파일명과 저장 후 탭에 표시된 파일명, 저장한 본문 일치, 저장 파일 편집 시 파일명 표시 유지
- 제목 변경 전후 본문·커서·수정 플래그·Undo/Redo 데이터 일치, 10만 줄 문서에서 제한 범위 탐색, 모듈 제거 후 세션 복원과 기본 편집

최신 Windows 배포판에서의 재실행, 명령 팔레트의 단축키 충돌 대화상자, Addons Manager의 제거 메뉴는 별도 실행 검증이 필요합니다. 제거 시험은 CudaText 종료 후 격리 복사본의 모듈 폴더를 이동하는 방식으로 수행했습니다.

패키징은 공식 `install.inf` 형식을 따릅니다. 등록 형식은 기본 제공 **Tabs List** 플러그인과 비교했고, **Tab Rename**도 CudaText 애드온 목록에서 확인했습니다. [패키징 문서](https://github.com/Alexey-T/CudaText/blob/master/wiki/cudatext_files_formats.wiki), [Tabs List 소스](https://github.com/CudaText-addons/cuda_tabs_list), [애드온 목록](https://github.com/Alexey-T/CudaText-registry/blob/master/json/plugins.json)
