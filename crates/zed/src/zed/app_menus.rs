use collab_ui::collab_panel;
use gpui::{App, Menu, MenuItem, OsAction};
use project::DisableAiSettings;
use release_channel::ReleaseChannel;
use settings::Settings;
use terminal_view::terminal_panel;
use zed_actions::{Quit, assistant, debug_panel, dev, git_panel, project_panel};

pub fn app_menus(cx: &mut App) -> Vec<Menu> {
    let mut view_items = vec![
        MenuItem::action(
            locale::t("Zoom In"),
            zed_actions::IncreaseBufferFontSize { persist: false },
        ),
        MenuItem::action(
            locale::t("Zoom Out"),
            zed_actions::DecreaseBufferFontSize { persist: false },
        ),
        MenuItem::action(
            locale::t("Reset Zoom"),
            zed_actions::ResetBufferFontSize { persist: false },
        ),
        MenuItem::action(
            locale::t("Reset All Zoom"),
            zed_actions::ResetAllZoom { persist: false },
        ),
        MenuItem::separator(),
        MenuItem::action(locale::t("Toggle Left Dock"), workspace::ToggleLeftDock),
        MenuItem::action(locale::t("Toggle Right Dock"), workspace::ToggleRightDock),
        MenuItem::action(locale::t("Toggle Bottom Dock"), workspace::ToggleBottomDock),
        MenuItem::action(locale::t("Toggle All Docks"), workspace::ToggleAllDocks),
        MenuItem::submenu(Menu {
            name: locale::t("Editor Layout"),
            disabled: false,
            items: vec![
                MenuItem::action(locale::t("Split Up"), workspace::SplitUp::default()),
                MenuItem::action(locale::t("Split Down"), workspace::SplitDown::default()),
                MenuItem::action(locale::t("Split Left"), workspace::SplitLeft::default()),
                MenuItem::action(locale::t("Split Right"), workspace::SplitRight::default()),
            ],
        }),
        MenuItem::separator(),
        MenuItem::action(locale::t("Project Panel"), project_panel::ToggleFocus),
        MenuItem::action(locale::t("Outline Panel"), outline_panel::ToggleFocus),
        MenuItem::action(locale::t("Collab Panel"), collab_panel::ToggleFocus),
        MenuItem::action(locale::t("Terminal Panel"), terminal_panel::Toggle),
        MenuItem::action(locale::t("Debugger Panel"), debug_panel::ToggleFocus),
    ];

    if !DisableAiSettings::get_global(cx).disable_ai {
        view_items.push(MenuItem::action(
            locale::t("Agent Panel"),
            assistant::ToggleFocus,
        ));
    }

    view_items.extend([
        MenuItem::action(locale::t("Git Panel"), git_panel::ToggleFocus),
        MenuItem::separator(),
        MenuItem::action(locale::t("Diagnostics"), diagnostics::Deploy),
        MenuItem::separator(),
    ]);

    if ReleaseChannel::try_global(cx) == Some(ReleaseChannel::Dev) {
        view_items.push(MenuItem::action(
            locale::t("Toggle GPUI Inspector"),
            dev::ToggleInspector,
        ));
        view_items.push(MenuItem::separator());
    }

    vec![
        Menu {
            name: locale::t("Zed"),
            disabled: false,
            items: vec![
                MenuItem::action(locale::t("About Zed"), zed_actions::About),
                MenuItem::action(locale::t("Check for Updates"), auto_update::Check),
                MenuItem::separator(),
                MenuItem::submenu(Menu::new(locale::t("Settings")).items([
                    MenuItem::action(locale::t("Open Settings"), zed_actions::OpenSettings),
                    MenuItem::action(locale::t("Open Settings File"), super::OpenSettingsFile),
                    MenuItem::action(
                        locale::t("Open Project Settings"),
                        zed_actions::OpenProjectSettings,
                    ),
                    MenuItem::action(
                        locale::t("Open Project Settings File"),
                        super::OpenProjectSettingsFile,
                    ),
                    MenuItem::action(
                        locale::t("Open Default Settings"),
                        super::OpenDefaultSettings,
                    ),
                    MenuItem::separator(),
                    MenuItem::action(locale::t("Open Keymap"), zed_actions::OpenKeymap),
                    MenuItem::action(locale::t("Open Keymap File"), zed_actions::OpenKeymapFile),
                    MenuItem::action(
                        locale::t("Open Default Key Bindings"),
                        zed_actions::OpenDefaultKeymap,
                    ),
                    MenuItem::separator(),
                    MenuItem::action(
                        locale::t("Select Theme..."),
                        zed_actions::theme_selector::Toggle::default(),
                    ),
                    MenuItem::action(
                        locale::t("Select Icon Theme..."),
                        zed_actions::icon_theme_selector::Toggle::default(),
                    ),
                ])),
                MenuItem::separator(),
                #[cfg(target_os = "macos")]
                MenuItem::os_submenu(locale::t("Services"), gpui::SystemMenuType::Services),
                MenuItem::separator(),
                MenuItem::action(locale::t("Extensions"), zed_actions::Extensions::default()),
                #[cfg(not(target_os = "windows"))]
                MenuItem::action(locale::t("Install CLI"), install_cli::InstallCliBinary),
                MenuItem::separator(),
                #[cfg(target_os = "macos")]
                MenuItem::action(locale::t("Hide Zed"), super::Hide),
                #[cfg(target_os = "macos")]
                MenuItem::action(locale::t("Hide Others"), super::HideOthers),
                #[cfg(target_os = "macos")]
                MenuItem::action(locale::t("Show All"), super::ShowAll),
                MenuItem::separator(),
                MenuItem::action(locale::t("Quit Zed"), Quit),
            ],
        },
        Menu {
            name: locale::t("File"),
            disabled: false,
            items: vec![
                MenuItem::action(locale::t("New"), workspace::NewFile),
                MenuItem::action(locale::t("New Window"), workspace::NewWindow),
                MenuItem::separator(),
                #[cfg(not(target_os = "macos"))]
                MenuItem::action(locale::t("Open File..."), workspace::OpenFiles),
                MenuItem::action(
                    locale::t(if cfg!(not(target_os = "macos")) {
                        "Open Folder..."
                    } else {
                        "Open…"
                    }),
                    workspace::Open::default(),
                ),
                MenuItem::action(
                    locale::t("Open Recent…"),
                    zed_actions::OpenRecent::default(),
                ),
                MenuItem::action(
                    locale::t("Open Remote…"),
                    zed_actions::OpenRemote::default(),
                ),
                MenuItem::separator(),
                MenuItem::action(
                    locale::t("Add Folder to Project…"),
                    workspace::AddFolderToProject,
                ),
                MenuItem::separator(),
                MenuItem::action(locale::t("Save"), workspace::Save { save_intent: None }),
                MenuItem::action(locale::t("Save As…"), workspace::SaveAs),
                MenuItem::action(
                    locale::t("Save All"),
                    workspace::SaveAll { save_intent: None },
                ),
                MenuItem::separator(),
                MenuItem::action(
                    locale::t("Close Editor"),
                    workspace::CloseActiveItem {
                        save_intent: None,
                        close_pinned: true,
                    },
                ),
                MenuItem::action(locale::t("Close Project"), workspace::CloseProject),
                MenuItem::action(locale::t("Close Window"), workspace::CloseWindow),
            ],
        },
        Menu {
            name: locale::t("Edit"),
            disabled: false,
            items: vec![
                MenuItem::os_action(locale::t("Undo"), editor::actions::Undo, OsAction::Undo),
                MenuItem::os_action(locale::t("Redo"), editor::actions::Redo, OsAction::Redo),
                MenuItem::separator(),
                MenuItem::os_action(locale::t("Cut"), editor::actions::Cut, OsAction::Cut),
                MenuItem::os_action(locale::t("Copy"), editor::actions::Copy, OsAction::Copy),
                MenuItem::action(locale::t("Copy and Trim"), editor::actions::CopyAndTrim),
                MenuItem::os_action(locale::t("Paste"), editor::actions::Paste, OsAction::Paste),
                MenuItem::separator(),
                MenuItem::action(locale::t("Find"), search::buffer_search::Deploy::find()),
                MenuItem::action(
                    locale::t("Find in Project"),
                    workspace::DeploySearch::default(),
                ),
                MenuItem::separator(),
                MenuItem::action(
                    locale::t("Toggle Line Comment"),
                    editor::actions::ToggleComments::default(),
                ),
            ],
        },
        Menu {
            name: locale::t("Selection"),
            disabled: false,
            items: vec![
                MenuItem::os_action(
                    locale::t("Select All"),
                    editor::actions::SelectAll,
                    OsAction::SelectAll,
                ),
                MenuItem::action(
                    locale::t("Expand Selection"),
                    editor::actions::SelectLargerSyntaxNode,
                ),
                MenuItem::action(
                    locale::t("Shrink Selection"),
                    editor::actions::SelectSmallerSyntaxNode,
                ),
                MenuItem::action(
                    locale::t("Select Next Sibling"),
                    editor::actions::SelectNextSyntaxNode,
                ),
                MenuItem::action(
                    locale::t("Select Previous Sibling"),
                    editor::actions::SelectPreviousSyntaxNode,
                ),
                MenuItem::separator(),
                MenuItem::action(
                    locale::t("Add Cursor Above"),
                    editor::actions::AddSelectionAbove {
                        skip_soft_wrap: true,
                    },
                ),
                MenuItem::action(
                    locale::t("Add Cursor Below"),
                    editor::actions::AddSelectionBelow {
                        skip_soft_wrap: true,
                    },
                ),
                MenuItem::action(
                    locale::t("Select Next Occurrence"),
                    editor::actions::SelectNext {
                        replace_newest: false,
                    },
                ),
                MenuItem::action(
                    locale::t("Select Previous Occurrence"),
                    editor::actions::SelectPrevious {
                        replace_newest: false,
                    },
                ),
                MenuItem::action(
                    locale::t("Select All Occurrences"),
                    editor::actions::SelectAllMatches,
                ),
                MenuItem::separator(),
                MenuItem::action(locale::t("Move Line Up"), editor::actions::MoveLineUp),
                MenuItem::action(locale::t("Move Line Down"), editor::actions::MoveLineDown),
                MenuItem::action(
                    locale::t("Duplicate Selection"),
                    editor::actions::DuplicateLineDown,
                ),
            ],
        },
        Menu {
            name: locale::t("View"),
            disabled: false,
            items: view_items,
        },
        Menu {
            name: locale::t("Go"),
            disabled: false,
            items: vec![
                MenuItem::action(locale::t("Back"), workspace::GoBack),
                MenuItem::action(locale::t("Forward"), workspace::GoForward),
                MenuItem::separator(),
                MenuItem::action(
                    locale::t("Command Palette..."),
                    zed_actions::command_palette::Toggle,
                ),
                MenuItem::separator(),
                MenuItem::action(
                    locale::t("Go to File..."),
                    workspace::ToggleFileFinder::default(),
                ),
                // MenuItem::action(locale::t("Go to Symbol in Project"), project_symbols::Toggle),
                MenuItem::action(
                    locale::t("Go to Symbol in Editor..."),
                    zed_actions::outline::ToggleOutline,
                ),
                MenuItem::action(
                    locale::t("Go to Line/Column..."),
                    editor::actions::ToggleGoToLine,
                ),
                MenuItem::separator(),
                MenuItem::action(
                    locale::t("Go to Definition"),
                    editor::actions::GoToDefinition::default(),
                ),
                MenuItem::action(
                    locale::t("Go to Declaration"),
                    editor::actions::GoToDeclaration::default(),
                ),
                MenuItem::action(
                    locale::t("Go to Type Definition"),
                    editor::actions::GoToTypeDefinition::default(),
                ),
                MenuItem::action(
                    locale::t("Find All References"),
                    editor::actions::FindAllReferences::default(),
                ),
                MenuItem::action(
                    locale::t("Show Incoming Calls"),
                    call_hierarchy::ShowIncomingCalls,
                ),
                MenuItem::action(
                    locale::t("Show Outgoing Calls"),
                    call_hierarchy::ShowOutgoingCalls,
                ),
                MenuItem::separator(),
                MenuItem::action(
                    locale::t("Next Problem"),
                    editor::actions::GoToDiagnostic::default(),
                ),
                MenuItem::action(
                    locale::t("Previous Problem"),
                    editor::actions::GoToPreviousDiagnostic::default(),
                ),
            ],
        },
        Menu {
            name: locale::t("Run"),
            disabled: false,
            items: vec![
                MenuItem::action(
                    locale::t("Spawn Task"),
                    zed_actions::Spawn::ViaModal {
                        reveal_target: None,
                    },
                ),
                MenuItem::action(locale::t("Start Debugger"), debugger_ui::Start),
                MenuItem::separator(),
                MenuItem::action(locale::t("Edit tasks.json…"), zed_actions::OpenProjectTasks),
                MenuItem::action(
                    locale::t("Edit debug.json…"),
                    zed_actions::OpenProjectDebugTasks,
                ),
                MenuItem::separator(),
                MenuItem::action(locale::t("Continue"), debugger_ui::Continue),
                MenuItem::action(locale::t("Step Over"), debugger_ui::StepOver),
                MenuItem::action(locale::t("Step Into"), debugger_ui::StepInto),
                MenuItem::action(locale::t("Step Out"), debugger_ui::StepOut),
                MenuItem::separator(),
                MenuItem::action(
                    locale::t("Toggle Breakpoint"),
                    editor::actions::ToggleBreakpoint,
                ),
                MenuItem::action(
                    locale::t("Edit Breakpoint"),
                    editor::actions::EditLogBreakpoint,
                ),
                MenuItem::action(
                    locale::t("Clear All Breakpoints"),
                    debugger_ui::ClearAllBreakpoints,
                ),
            ],
        },
        Menu {
            name: locale::t("Window"),
            disabled: false,
            items: vec![
                MenuItem::action(locale::t("Minimize"), super::Minimize),
                MenuItem::action(locale::t("Zoom"), super::Zoom),
                MenuItem::separator(),
            ],
        },
        Menu {
            name: locale::t("Help"),
            disabled: false,
            items: vec![
                MenuItem::action(
                    locale::t("View Release Notes Locally"),
                    auto_update_ui::ViewReleaseNotesLocally,
                ),
                MenuItem::action(locale::t("View Telemetry"), zed_actions::OpenTelemetryLog),
                MenuItem::action(
                    locale::t("View Dependency Licenses"),
                    zed_actions::OpenLicenses,
                ),
                MenuItem::action(locale::t("Show Welcome"), onboarding::ShowWelcome),
                MenuItem::separator(),
                MenuItem::action(
                    locale::t("File Bug Report..."),
                    zed_actions::feedback::FileBugReport,
                ),
                MenuItem::action(
                    locale::t("Request Feature..."),
                    zed_actions::feedback::RequestFeature,
                ),
                MenuItem::action(locale::t("Email Us..."), zed_actions::feedback::EmailZed),
                MenuItem::separator(),
                MenuItem::action(
                    locale::t("Documentation"),
                    super::OpenBrowser {
                        url: "https://zed.dev/docs".into(),
                    },
                ),
                MenuItem::action(locale::t("Zed Repository"), feedback::OpenZedRepo),
                MenuItem::action(
                    locale::t("Zed Twitter"),
                    super::OpenBrowser {
                        url: "https://twitter.com/zeddotdev".into(),
                    },
                ),
                MenuItem::action(
                    locale::t("Join the Team"),
                    super::OpenBrowser {
                        url: "https://zed.dev/jobs".into(),
                    },
                ),
            ],
        },
    ]
}
