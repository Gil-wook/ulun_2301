# uLaunch 23.0.1 개발 빌드 검증 기록

## 결론

- 검증일: 2026-10-23 KST (GitHub 실행 시각은 2026-10-22 UTC).
- [성공 실행](https://github.com/Gil-wook/ulun_2301/actions/runs/39831164539): `completed / success`.
- 실행 소스 커밋: `dd00d5ae06f73781308fa0a6227a8f63348bd662`.
- 전달용 소스는 성공 실행의 원본에서 생성된 `.gch` 캐시만 제거해 다시 압축했다. 바이너리 ZIP과 소스 파일 내용은 바꾸지 않았다.
- 네 구성요소 uSystem·uLoader·uMenu·uManager의 컴파일, 패키징, 산출물 업로드가 모두 성공했다.
- 다운로드한 실제 ZIP과 대응 소스를 별도로 검사했다. 모의 파일로 실제 빌드를 대체하지 않았다.
- **Switch 실기기에서 실행하지 않았다. 펌웨어 23.0.1 호환성이나 설치 안전성을 보증하지 않는다.**
- Java PC 도구 uScreen과 테마 편집기 uDesigner는 빌드 대상이 아니다.

## 첫 실패와 수정

[첫 실행](https://github.com/Gil-wook/ulun_2301/actions/runs/39830881431)은 공식 SDK 패키지 서버가
`dkp-libs.db`와 `dkp-linux.db` 요청에 HTTP 403을 반환해 SDK 준비 단계에서 실패했다.

고정된 공식 devkitPro 이미지에 이미 필요한 SDK 그룹과 도구가 있으므로, 실시간 패키지 업데이트 대신
이미지 스냅샷을 명시적으로 사용하도록 수정했다. 필수 패키지 그룹·도구가 없으면 실패하며,
서명 검증을 끄거나 부분 빌드를 정상 산출물로 처리하지 않는다.

수정 후 전체 빌드가 통과했다. 추가 C++ 패치는 필요하지 않았다. 워크플로는 여전히 로컬 소스가 아닌
고정된 공개 소스를 가져오므로, 앞으로 C++를 수정하면 원격 빌드에도 반영해야 한다.

전달 단계에서 원본 소스 압축에 약 517 MB의 생성된 사전 컴파일 헤더 캐시가 포함된 것을 확인했다.
전달용 소스는 `.gch` 디렉터리와 그 안의 캐시 파일만 제거하고 재압축했다. 이 정리는 소스 수정이나 재컴파일이 아니다.
바이너리 ZIP은 원격 원본과 동일하며, 소스 체크섬은 정리 전후가 다르다. 원본과 정리본은 각각 구분해 기록했다.
워크플로에도 `.gch`·`.pch` 제외 규칙을 추가했으며, 이 압축 규칙 수정 후 전체 원격 재빌드는 하지 않았다.
동봉한 `build-recipe/successful-build-ulaunch.yml`은 성공 실행 당시의 정확한 설정이고,
`.github/workflows/build-ulaunch.yml`은 캐시 제외 규칙을 추가한 설정이다.

## 빌드 입력

| 항목 | 고정 버전 |
| --- | --- |
| uLaunch | `6da94f9164f5fa61380010008270457f95ff4b04` |
| Atmosphere-libs | `cf48d23375cf36742876f4b014971b2ebabc6dc8` |
| libnx | `b156b4774fb2df7b93402169509266da7547fc4c` |
| SDL2 레시피 | `0ae8790f6e092cf8df937d143e70a785f7e27997` |
| SDL2 | 2.28.5-3, 소스와 패치 체크섬 확인 후 재빌드 |
| 공식 devkitPro 이미지 | `devkitpro/devkita64@sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282` |
| 컴파일러 | devkitA64 GCC 15.2.0 |

`sdk-packages.txt`는 이미지의 패키지 데이터베이스이다. 소스에서 덮어쓴 libnx·SDL2의 실제 입력은
위 커밋·레시피와 `03-libnx.log`, `04-sdl2.log`가 기준이다.

## 실제 산출물 검사

`scripts/verify-ulaunch-release.py`로 다음을 확인했다.

- ZIP과 대응 소스의 SHA-256 일치.
- ZIP 전체 CRC, 중복·위험 경로 검사.
- 필수 바이너리 10개의 존재와 PFS0·NSO0·META·NRO0·RomFS 헤더 확인.
- 두 위치의 uSystem 패키지가 바이트 단위로 일치.
- ZIP 안팎의 빌드 정보 일치와 성공 실행 URL 확인.
- uLaunch·nx-hbloader 라이선스 포함.
- 대응 소스의 네 프로젝트 Makefile·진입점, ARC 생성 도구, libnx, 의존 라이브러리 라이선스,
  SDL2 소스·패치·레시피, 개발 마이크로 버전 6 확인.
- 소스 압축에 생성된 실행 바이너리가 포함되지 않은 것 확인.

검증 도구의 누락·손상·다른 실행 정보·위험 경로·소스 버전·컴파일 캐시 오류 검출 테스트 9개도 통과했다.
이 검사는 파일 구성과 무결성에 관한 것으로, 바이너리 실행 테스트가 아니다.

| 필수 파일 | 바이트 |
| --- | ---: |
| `atmosphere/contents/0100000000001000/exefs.nsp` | 598665 |
| `ulaunch/bin/uSystem/exefs.nsp` | 598665 |
| `ulaunch/bin/uMenu/main` | 6822721 |
| `ulaunch/bin/uMenu/main.npdm` | 964 |
| `ulaunch/bin/uMenu/romfs.bin` | 597272 |
| `ulaunch/bin/uLoader/applet/main` | 175183 |
| `ulaunch/bin/uLoader/applet/main.npdm` | 992 |
| `ulaunch/bin/uLoader/application/main` | 175183 |
| `ulaunch/bin/uLoader/application/main.npdm` | 988 |
| `switch/uManager.nro` | 10178625 |

## SHA-256

```text
206f785206aba8df796c3723f0f4078b051b7f6250ece00beaa2be253e77b40e  uLaunch-23.0.1-dev.zip
997e50a5975864582842998ce06cc3d4a8f4eccfb138464c2f7f80e6118795ba  uLaunch-23.0.1-dev-source.tar.gz
```

위 소스 체크섬은 전달용 정리본 기준이다. GitHub 성공 실행의 캐시 포함 원본 소스 체크섬은
`093dfefcfa614c792ab9e0a1c93b551caaefafced665d7d13b07d432e0be2684`이다.
`source-cleanup.json`과 `source-cleanup-comparison.json`에 정리 대상·전후 체크섬과 나머지 파일 일치 검사를 남겼다.
캐시를 제외한 6,912개 항목의 이름·형식·권한·크기·링크 대상을 비교했고, 일반 파일 5,927개는 내용의 SHA-256도 일치했다.

## 받는 파일과 보관

- `uLaunch-23.0.1-dev.zip`: 원격 빌드가 생성한 개발용 바이너리 ZIP.
- `uLaunch-23.0.1-dev-source.tar.gz`: 같은 실행의 수정 소스·의존 소스와 라이선스에서 생성된 컴파일 캐시만 제거한 정리본.
- `uLaunch-23.0.1-dev-complete.zip`: 위 두 파일에 빌드 설정, SDK 목록, 로그, 검증 기록과 검사 도구를 함께 넣은 편의용 전체 묶음.

전체 묶음은 SD 카드에 바로 풀기 위한 설치 ZIP이 아니다. 그 안의 개발 ZIP은 원본 바이트를 유지했다.
다음 수정에는 대응 소스와 빌드 설정을 함께 사용한다. GitHub Artifacts는 14일 보관으로 설정되어 있으므로
장기 보관이 필요하면 전체 묶음을 별도로 보관한다.

소스·SDK 조합의 빌드 성공만 확인된 개발 버전이다. 유일한 SD 카드 사본에 덮어쓰지 말고,
배포할 때는 해당 빌드의 대응 소스와 라이선스도 함께 제공한다.
