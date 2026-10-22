#!/usr/bin/env python3
"""Apply the port's startup trace markers to the pinned upstream source."""

from pathlib import Path
import sys


def replace_once(text: str, before: str, after: str, label: str) -> str:
    count = text.count(before)
    if count != 1:
        raise SystemExit(f"Expected one upstream anchor for {label}, found {count}")
    return text.replace(before, after, 1)


def patch_file(path: Path, replacements: list[tuple[str, str, str]]) -> None:
    data = path.read_bytes()
    newline = "\r\n" if b"\r\n" in data else "\n"
    text = data.decode("utf-8").replace("\r\n", "\n")

    if "BOOTTRACE component=" in text:
        raise SystemExit(f"Refusing to patch an already instrumented file: {path}")

    for before, after, label in replacements:
        text = replace_once(text, before, after, label)

    path.write_bytes(text.replace("\n", newline).encode("utf-8"))


def apply(source: Path) -> None:
    patch_file(
        source / "projects/uSystem/source/main.cpp",
        [
            (
                """    void Initialize() {
        UL_RC_ASSERT(appletLoadAndApplyIdlePolicySettings());
        UpdateOperationMode();""",
                """    void Initialize() {
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=initialize.begin");
        UL_RC_ASSERT(appletLoadAndApplyIdlePolicySettings());
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=idle-policy.ready");
        UpdateOperationMode();
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=operation-mode.ready");""",
                "uSystem initialization start",
            ),
            (
                "        g_AmsIsEmuMMC = ul::os::IsEmuMMC();",
                """        g_AmsIsEmuMMC = ul::os::IsEmuMMC();
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=emummc.detected value=%d", g_AmsIsEmuMMC.load());""",
                "uSystem emuMMC detection",
            ),
            (
                "        ul::fs::CreateDirectory(ul::RootCachePath);",
                """        ul::fs::CreateDirectory(ul::RootCachePath);
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=cache-root.ready");""",
                "uSystem cache setup",
            ),
            (
                """        ul::fs::CleanDirectory(ul::ThemePreviewCachePath);

        g_CurrentRecords = ul::os::ListApplicationRecords();""",
                """        ul::fs::CleanDirectory(ul::ThemePreviewCachePath);

        g_CurrentRecords = ul::os::ListApplicationRecords();
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=application-records.loaded count=%zu", g_CurrentRecords.size());""",
                "uSystem application records",
            ),
            (
                "        CheckHomebrewTakeoverApplicationId();",
                """        CheckHomebrewTakeoverApplicationId();
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=application-cache.ready");""",
                "uSystem application cache",
            ),
            (
                """        // Test, until we figure out how to check if apps need updates
        DebugLogApplicationParameters();

        LoadConfig();

        UL_RC_ASSERT(sf::Initialize());""",
                """        // Test, until we figure out how to check if apps need updates
        DebugLogApplicationParameters();

        LoadConfig();
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=config.loaded");

        UL_RC_ASSERT(sf::Initialize());
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=private-service.ready");""",
                "uSystem configuration and private service",
            ),
            (
                "        UL_RC_ASSERT(threadStart(&g_EventManagerThread));",
                """        UL_RC_ASSERT(threadStart(&g_EventManagerThread));
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=event-manager.ready");""",
                "uSystem event manager",
            ),
            (
                "            UL_RC_ASSERT(threadStart(&g_UsbViewerWriteThread));\n        }\n    }\n\n}",
                """            UL_RC_ASSERT(threadStart(&g_UsbViewerWriteThread));
        }
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=initialize.complete");
    }

}""",
                "uSystem initialization completion",
            ),
            (
                "            ul::InitializeLogging(\"uSystem\");",
                """            ul::InitializeLogging("uSystem");
            UL_LOG_INFO("BOOTTRACE component=uSystem stage=system-module-services.ready build=%u.%u.%u",
                static_cast<u32>(ul::CurrentVersion.major), static_cast<u32>(ul::CurrentVersion.minor), static_cast<u32>(ul::CurrentVersion.micro));""",
                "uSystem logger start",
            ),
            (
                "    void Main() {\n        // Initialize everything\n        Initialize();",
                """    void Main() {
        // Initialize everything
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=main.begin");
        Initialize();
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=main.initialize.complete");""",
                "uSystem main entry",
            ),
            (
                "        // After having initialized everything, launch our menu\n        UL_RC_ASSERT(LaunchMenu(ul::smi::MenuStartMode::StartupMenuPostBoot));",
                """        // After having initialized everything, launch our menu
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=menu-launch.begin");
        UL_RC_ASSERT(LaunchMenu(ul::smi::MenuStartMode::StartupMenuPostBoot));
        UL_LOG_INFO("BOOTTRACE component=uSystem stage=menu-launch.returned");""",
                "uSystem menu handoff",
            ),
        ],
    )

    patch_file(
        source / "projects/uMenu/source/main.cpp",
        [
            (
                """        UL_RC_ASSERT(fsInitialize());
        UL_RC_ASSERT(fsdevMountSdmc());

        UL_RC_ASSERT(timeInitialize());
        __libnx_init_time();

        ul::InitializeLogging("uMenu");
        UL_LOG_INFO("Alive!");""",
                """        UL_RC_ASSERT(fsInitialize());
        UL_RC_ASSERT(fsdevMountSdmc());
        ul::InitializeLogging("uMenu");
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=sd-mounted build=%u.%u.%u",
            static_cast<u32>(ul::CurrentVersion.major), static_cast<u32>(ul::CurrentVersion.minor), static_cast<u32>(ul::CurrentVersion.micro));

        UL_RC_ASSERT(timeInitialize());
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=time-service.ready");
        __libnx_init_time();
        UL_LOG_INFO("Alive!");""",
                "uMenu early logger",
            ),
            (
                "        hosversionSet(MAKEHOSVERSION(g_FirmwareVersion.major, g_FirmwareVersion.minor, g_FirmwareVersion.micro) | BIT(31));",
                """        hosversionSet(MAKEHOSVERSION(g_FirmwareVersion.major, g_FirmwareVersion.minor, g_FirmwareVersion.micro) | BIT(31));
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=settings-services.ready firmware=%u.%u.%u",
            static_cast<u32>(g_FirmwareVersion.major), static_cast<u32>(g_FirmwareVersion.minor), static_cast<u32>(g_FirmwareVersion.micro));""",
                "uMenu firmware version",
            ),
            (
                "        UL_RC_ASSERT(psmInitialize());",
                """        UL_RC_ASSERT(psmInitialize());
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=system-services.ready");""",
                "uMenu service setup",
            ),
            (
                "        __nx_win_init();",
                """        __nx_win_init();
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=window-system.ready");""",
                "uMenu window setup",
            ),
            (
                """    void InitializeSettings() {
        UL_LOG_INFO("Initializing settings...");
        g_GlobalSettings = {};""",
                """    void InitializeSettings() {
        UL_LOG_INFO("Initializing settings...");
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=settings.begin");
        g_GlobalSettings = {};""",
                "uMenu settings start",
            ),
            (
                """        ul::os::GetAmsConfig(g_GlobalSettings.ams_version, g_GlobalSettings.ams_is_emummc);
        g_GlobalSettings.fw_version = g_FirmwareVersion;""",
                """        ul::os::GetAmsConfig(g_GlobalSettings.ams_version, g_GlobalSettings.ams_is_emummc);
        g_GlobalSettings.fw_version = g_FirmwareVersion;
        const auto atmosphere_version = g_GlobalSettings.ams_version.Format();
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=environment.detected atmosphere=%s firmware=%u.%u.%u emummc=%d",
            atmosphere_version.c_str(), static_cast<u32>(g_FirmwareVersion.major), static_cast<u32>(g_FirmwareVersion.minor),
            static_cast<u32>(g_FirmwareVersion.micro), g_GlobalSettings.ams_is_emummc);""",
                "uMenu environment versions",
            ),
            (
                "        UL_RC_ASSERT(setsysGetBatteryLot(&g_GlobalSettings.battery_lot));\n    }\n\n    void MainLoop()",
                """        UL_RC_ASSERT(setsysGetBatteryLot(&g_GlobalSettings.battery_lot));
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=settings.complete");
    }

    void MainLoop()""",
                "uMenu settings completion",
            ),
            (
                "    void MainLoop() {\n        // Load menu config\n        g_GlobalSettings.config = ul::cfg::LoadConfig();",
                """    void MainLoop() {
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=main-loop.begin");
        // Load menu config
        g_GlobalSettings.config = ul::cfg::LoadConfig();
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=config.loaded");""",
                "uMenu main loop and configuration",
            ),
            (
                """        if(g_GlobalSettings.system_status.reload_theme_cache) {
            ul::cfg::CacheActiveTheme(g_GlobalSettings.config);
        }""",
                """        if(g_GlobalSettings.system_status.reload_theme_cache) {
            UL_LOG_INFO("BOOTTRACE component=uMenu stage=theme-cache.refresh.begin");
            ul::cfg::CacheActiveTheme(g_GlobalSettings.config);
            UL_LOG_INFO("BOOTTRACE component=uMenu stage=theme-cache.refresh.complete");
        }""",
                "uMenu theme cache",
            ),
            (
                """        if(!active_theme_name.empty()) {
            const auto rc = ul::cfg::TryLoadTheme(active_theme_name, g_GlobalSettings.active_theme);
            if(R_SUCCEEDED(rc)) {
                ul::cfg::EnsureCacheActiveTheme(g_GlobalSettings.config);""",
                """        if(!active_theme_name.empty()) {
            UL_LOG_INFO("BOOTTRACE component=uMenu stage=theme.load.begin");
            const auto rc = ul::cfg::TryLoadTheme(active_theme_name, g_GlobalSettings.active_theme);
            if(R_SUCCEEDED(rc)) {
                ul::cfg::EnsureCacheActiveTheme(g_GlobalSettings.config);
                UL_LOG_INFO("BOOTTRACE component=uMenu stage=theme.load.complete");""",
                "uMenu theme load",
            ),
            (
                "        ul::cfg::LoadLanguageJsons(ul::MenuLanguagesPath, g_GlobalSettings.main_lang, g_GlobalSettings.default_lang);",
                """        ul::cfg::LoadLanguageJsons(ul::MenuLanguagesPath, g_GlobalSettings.main_lang, g_GlobalSettings.default_lang);
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=translations.loaded");""",
                "uMenu translations",
            ),
            (
                """        auto renderer = pu::ui::render::Renderer::New(renderer_opts);
        g_MenuApplication = ul::menu::ui::MenuApplication::New(renderer);

        UL_ASSERT_TRUE(pu::audio::Initialize(MIX_INIT_MP3));

        g_MenuApplication->Initialize(g_StartMode);""",
                """        auto renderer = pu::ui::render::Renderer::New(renderer_opts);
        g_MenuApplication = ul::menu::ui::MenuApplication::New(renderer);
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=renderer.created");

        UL_ASSERT_TRUE(pu::audio::Initialize(MIX_INIT_MP3));
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=audio.ready");

        g_MenuApplication->Initialize(g_StartMode);
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=menu-application.initialized");""",
                "uMenu renderer and audio",
            ),
            (
                "        UL_RC_ASSERT(g_MenuApplication->Load());",
                """        UL_RC_ASSERT(g_MenuApplication->Load());
        UL_LOG_INFO("BOOTTRACE component=uMenu stage=menu-loaded");""",
                "uMenu menu load",
            ),
            (
                "        if(g_StartMode == ul::smi::MenuStartMode::StartupMenuPostBoot) {\n            g_MenuApplication->ShowWithFadeIn();\n        }\n        else {\n            g_MenuApplication->Show();",
                """        if(g_StartMode == ul::smi::MenuStartMode::StartupMenuPostBoot) {
            UL_LOG_INFO("BOOTTRACE component=uMenu stage=menu-show.fade-in");
            g_MenuApplication->ShowWithFadeIn();
        }
        else {
            UL_LOG_INFO("BOOTTRACE component=uMenu stage=menu-show");
            g_MenuApplication->Show();""",
                "uMenu screen presentation",
            ),
            (
                "int main() {\n    InitializeSettings();",
                """int main() {
    UL_LOG_INFO("BOOTTRACE component=uMenu stage=main.begin");
    InitializeSettings();
    UL_LOG_INFO("BOOTTRACE component=uMenu stage=settings.ready");""",
                "uMenu main entry",
            ),
            (
                "    UL_ASSERT_TRUE(g_StartMode != ul::smi::MenuStartMode::Invalid);",
                """    UL_ASSERT_TRUE(g_StartMode != ul::smi::MenuStartMode::Invalid);
    UL_LOG_INFO("BOOTTRACE component=uMenu stage=start-mode.read value=%u", static_cast<u32>(g_StartMode));""",
                "uMenu start mode",
            ),
            (
                '    UL_RC_ASSERT(romfsMountFromFsdev(ul::MenuRomfsFile, 0, "romfs"));',
                """    UL_RC_ASSERT(romfsMountFromFsdev(ul::MenuRomfsFile, 0, "romfs"));
    UL_LOG_INFO("BOOTTRACE component=uMenu stage=romfs.mounted");""",
                "uMenu RomFS mount",
            ),
            (
                "    ul::menu::ui::QuickMenu::RegisterHomeButtonDetection();\n\n    MainLoop();",
                """    ul::menu::ui::QuickMenu::RegisterHomeButtonDetection();

    UL_LOG_INFO("BOOTTRACE component=uMenu stage=main-loop.call");
    MainLoop();""",
                "uMenu main loop call",
            ),
        ],
    )

    patch_file(
        source / "libs/uCommon/source/ul/util/util_Json.cpp",
        [
            (
                "                out_json = JSON::parse(json_str);\n                return ResultSuccess;",
                """                out_json = JSON::parse(json_str, nullptr, false);
                if(out_json.is_discarded() || !out_json.is_object()) {
                    UL_LOG_WARN("Invalid JSON file '%s'", path.c_str());
                    out_json = JSON::object();
                    return ResultInvalidJson;
                }
                return ResultSuccess;""",
                "non-throwing JSON file parsing",
            ),
        ],
    )

    patch_file(
        source / "libs/uCommon/source/ul/cfg/cfg_Config.cpp",
        [
            (
                "        const auto manifest_json = util::JSON::parse(manifest_json_str);",
                """        const auto manifest_json = util::JSON::parse(manifest_json_str, nullptr, false);
        if(manifest_json.is_discarded() || !manifest_json.is_object()) {
            UL_LOG_WARN("Invalid JSON in theme manifest '%s'", theme_path.c_str());
            return ResultInvalidJson;
        }
        if((manifest_json.contains("format_version") && !manifest_json["format_version"].is_number_unsigned()) ||
           (manifest_json.contains("name") && !manifest_json["name"].is_string()) ||
           (manifest_json.contains("author") && !manifest_json["author"].is_string()) ||
           (manifest_json.contains("description") && !manifest_json["description"].is_string()) ||
           (manifest_json.contains("release") && !manifest_json["release"].is_string())) {
            UL_LOG_WARN("Invalid field type in theme manifest '%s'", theme_path.c_str());
            return ResultInvalidJson;
        }
        """,
                "non-throwing and validated theme manifest parsing",
            ),
        ],
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply-ulaunch-boot-trace.py SOURCE_DIR")
    apply(Path(sys.argv[1]))
