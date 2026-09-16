//! UI language support for Zed's Simplified Chinese localization.
//!
//! GUI labels only: never use this crate for model prompts, tool schemas,
//! protocol fields, telemetry names, or anything else observed by AI models.
//! See `assets/locales/SCHEMA.md` for the dictionary format and
//! `assets/locales/GLOSSARY.md` for terminology.

use std::sync::atomic::{AtomicU8, Ordering};
use std::sync::{OnceLock, RwLock};

use collections::HashMap;
use gpui_shared_string::SharedString;

/// Dictionary compiled in from `assets/locales/zh-CN.json`.
const DEFAULT_DICTIONARY_JSON: &str = include_str!("../../../assets/locales/zh-CN.json");

/// Action display names compiled in from `assets/locales/actions-zh-CN.json`,
/// keyed by action ID (`workspace::NewFile`).
const ACTIONS_DICTIONARY_JSON: &str = include_str!("../../../assets/locales/actions-zh-CN.json");

/// Language selected for Zed's user interface.
///
/// The default follows the operating system locale, so users on Chinese
/// systems get Chinese without changing any setting.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Language {
    /// Follow the operating system locale.
    #[default]
    System,
    /// Always English.
    English,
    /// Always Simplified Chinese.
    SimplifiedChinese,
}

// Where the language comes from, in priority order:
//
// 1. an explicit override (`set_language`, used by tests to assert against
//    the English source strings regardless of the machine's locale);
// 2. the `language` setting (`sync_language`, refreshed by
//    `LanguageSetting::from_settings` whenever settings are (re)loaded);
// 3. the operating system locale (`Language::System`).

/// Explicit override set via [`set_language`]; never overwritten by the
/// settings layer, so a test that pins English stays English.
static EXPLICIT_LANGUAGE: RwLock<Option<Language>> = RwLock::new(None);

/// Mirror of the `language` setting, refreshed by [`sync_language`].
static SETTING_LANGUAGE: RwLock<Option<Language>> = RwLock::new(None);

const STATE_UNINITIALIZED: u8 = 0;
const STATE_ENGLISH: u8 = 1;
const STATE_CHINESE: u8 = 2;

/// Cached active language state for hot rendering path (`use_chinese`).
/// Updated whenever explicit override or settings mirror changes, avoiding
/// locks, syscalls and allocations during frame rendering.
static USE_CHINESE_STATE: AtomicU8 = AtomicU8::new(STATE_UNINITIALIZED);

/// Parses a compiled-in dictionary of English source text to translation.
///
/// Values are stored as [`SharedString`] so that a lookup only bumps a
/// reference count instead of rebuilding the string on every call — `t()` runs
/// once per label per frame. `SharedString` is not `Deserialize`, hence the
/// intermediate `HashMap<String, String>`.
fn parse_dictionary(json: &str) -> HashMap<String, SharedString> {
    serde_json::from_str::<HashMap<String, String>>(json)
        .unwrap_or_default()
        .into_iter()
        .map(|(source, translation)| (source, SharedString::from(translation)))
        .collect()
}

fn dictionary() -> &'static HashMap<String, SharedString> {
    static DICTIONARY: OnceLock<HashMap<String, SharedString>> = OnceLock::new();
    DICTIONARY.get_or_init(|| parse_dictionary(DEFAULT_DICTIONARY_JSON))
}

fn actions_dictionary() -> &'static HashMap<String, SharedString> {
    static ACTIONS_DICTIONARY: OnceLock<HashMap<String, SharedString>> = OnceLock::new();
    ACTIONS_DICTIONARY.get_or_init(|| parse_dictionary(ACTIONS_DICTIONARY_JSON))
}

fn explicit_language() -> Option<Language> {
    EXPLICIT_LANGUAGE.read().ok().and_then(|guard| *guard)
}

fn setting_language() -> Option<Language> {
    SETTING_LANGUAGE.read().ok().and_then(|guard| *guard)
}

/// Returns true for Chinese locale identifiers
/// (`zh`, `zh-CN`, `zh_Hans`, `zh-Hant-TW`, ...).
pub fn is_chinese_locale(locale: &str) -> bool {
    let normalized = locale.replace('_', "-");
    normalized
        .split('-')
        .next()
        .is_some_and(|language| language.eq_ignore_ascii_case("zh"))
}

/// Evaluates OS locale once and caches the result.
fn system_locale_is_chinese() -> bool {
    static IS_CHINESE: OnceLock<bool> = OnceLock::new();
    *IS_CHINESE.get_or_init(|| {
        let system_locale = sys_locale::get_locale().unwrap_or_else(|| String::from("en-US"));
        is_chinese_locale(&system_locale)
    })
}

/// Detects whether the current process is running as a test runner.
/// Test binaries built by Cargo are placed in target/.../deps/.
fn is_test_runner() -> bool {
    static IS_TEST: OnceLock<bool> = OnceLock::new();
    *IS_TEST.get_or_init(|| {
        std::env::current_exe().is_ok_and(|path| {
            path.parent()
                .and_then(|p| p.file_name())
                .is_some_and(|name| name == "deps")
        })
    })
}

/// The language the UI currently renders in, resolving [`Language::System`]
/// against the operating system locale (defaulting to English in test runners).
fn effective_language() -> Language {
    match explicit_language()
        .or_else(setting_language)
        .unwrap_or(Language::System)
    {
        Language::System => {
            // Tests assert against English labels by default, so test runners
            // default to English unless explicitly configured or overridden.
            if is_test_runner() && std::env::var_os("ZED_TEST_CHINESE").is_none() {
                Language::English
            } else if system_locale_is_chinese() {
                Language::SimplifiedChinese
            } else {
                Language::English
            }
        }
        language => language,
    }
}

fn update_effective_language_state() {
    let state = if effective_language() == Language::SimplifiedChinese {
        STATE_CHINESE
    } else {
        STATE_ENGLISH
    };
    USE_CHINESE_STATE.store(state, Ordering::Release);
}

/// Whether the UI should currently render Simplified Chinese.
/// Zero-allocation, lock-free check on the hot render path.
pub fn use_chinese() -> bool {
    match USE_CHINESE_STATE.load(Ordering::Relaxed) {
        STATE_CHINESE => true,
        STATE_ENGLISH => false,
        _ => {
            update_effective_language_state();
            USE_CHINESE_STATE.load(Ordering::Relaxed) == STATE_CHINESE
        }
    }
}

/// Pin the UI language to an explicit override.
///
/// The override outranks the `language` setting, so it is not clobbered when
/// settings are reloaded. Tests use it to assert against the English source
/// strings no matter which locale the machine runs; remember to
/// [`clear_language_overrides`] afterwards if the language matters.
pub fn set_language(language: Language) {
    if let Ok(mut guard) = EXPLICIT_LANGUAGE.write() {
        *guard = Some(language);
    }
    update_effective_language_state();
}

/// Follow the `language` setting.
///
/// Called by `LanguageSetting::from_settings` on every settings (re)load;
/// ignored while an explicit override is set via [`set_language`].
pub fn sync_language(language: Language) {
    if explicit_language().is_some() {
        return;
    }
    if let Ok(mut guard) = SETTING_LANGUAGE.write() {
        *guard = Some(language);
    }
    update_effective_language_state();
}

/// Drop the explicit override and the setting mirror, falling back to the
/// operating system locale.
pub fn clear_language_overrides() {
    if let Ok(mut guard) = EXPLICIT_LANGUAGE.write() {
        *guard = None;
    }
    if let Ok(mut guard) = SETTING_LANGUAGE.write() {
        *guard = None;
    }
    update_effective_language_state();
}

/// Translate a GUI label, falling back to the English source text when
/// Chinese is not active or no translation exists. Never panics.
pub fn t(key: &str) -> SharedString {
    if !use_chinese() {
        return SharedString::from(key);
    }
    dictionary()
        .get(key)
        .cloned()
        .unwrap_or_else(|| SharedString::from(key))
}

/// Translate a GUI label containing `{placeholder}` slots, substituting each
/// pair after lookup. Falls back to the English source text like [`t`].
/// Placeholders must match `assets/locales/SCHEMA.md` (checked by tests).
pub fn t_format(key: &str, replacements: &[(&str, &str)]) -> SharedString {
    let translated = if use_chinese() {
        dictionary()
            .get(key)
            .map(|translated| translated.as_str())
            .unwrap_or(key)
    } else {
        key
    };
    let mut result = translated.to_string();
    for (placeholder, value) in replacements {
        result = result.replacen(placeholder, value, 1);
    }
    SharedString::from(result)
}

/// Display name for a command palette action: `中文 (english)` when Chinese
/// is active and a translation exists, otherwise the English name unchanged.
///
/// Matching keeps working in both languages because the combined string
/// contains the English name.
pub fn localized_action_name(action_id: &str, english: &str) -> SharedString {
    if !use_chinese() {
        return SharedString::from(english);
    }
    match actions_dictionary().get(action_id) {
        Some(translated) => SharedString::from(format!("{translated} ({english})")),
        None => SharedString::from(english),
    }
}

/// Placeholder names (`{name}`) in a source text that a translation must keep.
pub fn placeholders(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut rest = text;
    while let Some(start) = rest.find('{') {
        rest = &rest[start + 1..];
        // Skip escaped `{{`.
        if rest.starts_with('{') {
            rest = &rest[1..];
            continue;
        }
        let Some(end) = rest.find('}') else {
            break;
        };
        out.push(rest[..end].to_string());
        rest = &rest[end + 1..];
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    // The language cells are process-global; serialize tests that mutate them.
    static TEST_LOCK: Mutex<()> = Mutex::new(());

    #[test]
    fn setting_sync_applies_without_explicit_override() {
        let _guard = TEST_LOCK.lock().unwrap();
        clear_language_overrides();

        // The settings layer mirrors the `language` setting.
        sync_language(Language::English);
        assert!(!use_chinese());
        sync_language(Language::SimplifiedChinese);
        assert!(use_chinese());

        // `System` falls back to the machine's locale, which is not asserted
        // here: the point is that the synced value is what gets used.
        sync_language(Language::System);
        clear_language_overrides();
    }

    #[test]
    fn explicit_override_survives_setting_sync() {
        let _guard = TEST_LOCK.lock().unwrap();
        clear_language_overrides();

        // A test pins English; the settings layer then re-syncs the default
        // `system` setting (as `Workspace::new` used to do). English must win,
        // otherwise prompt labels render in Chinese on a Chinese machine and
        // `simulate_prompt_answer("Trash")` cannot find its button.
        set_language(Language::English);
        sync_language(Language::System);
        assert!(!use_chinese());
        assert_eq!(t("Trash"), "Trash");

        // …symmetrically for a pinned Chinese UI.
        set_language(Language::SimplifiedChinese);
        sync_language(Language::English);
        assert!(use_chinese());

        clear_language_overrides();
    }

    #[test]
    fn test_runner_defaults_to_english_under_system() {
        let _guard = TEST_LOCK.lock().unwrap();
        clear_language_overrides();

        assert_eq!(effective_language(), Language::English);
        assert!(!use_chinese());
    }

    #[test]
    fn detects_chinese_locales() {
        for locale in ["zh", "zh-CN", "zh_CN", "zh-Hans-CN", "zh-Hant-TW", "ZH-tw"] {
            assert!(
                is_chinese_locale(locale),
                "{locale} should count as Chinese"
            );
        }
        for locale in ["", "en", "en-US", "ja", "ko", "de-DE"] {
            assert!(
                !is_chinese_locale(locale),
                "{locale} should not count as Chinese"
            );
        }
    }

    #[test]
    fn extracts_placeholders() {
        assert!(placeholders("Open Settings").is_empty());
        assert_eq!(placeholders("Hello {name}"), vec!["name".to_string()]);
        assert_eq!(
            placeholders("{count} files in {folder}"),
            vec!["count".to_string(), "folder".to_string()]
        );
        // Escaped braces are not placeholders.
        assert!(placeholders("literal {{brace}}").is_empty());
    }

    #[test]
    fn formats_placeholders() {
        let _guard = TEST_LOCK.lock().unwrap();
        set_language(Language::English);
        assert_eq!(t_format("Hello {name}", &[("{name}", "Zed")]), "Hello Zed");
        // Real dictionary entry, substituted after lookup.
        set_language(Language::SimplifiedChinese);
        assert_eq!(
            t_format("Currently In Use: {name}", &[("{name}", "main")]),
            "正在使用：main"
        );
        clear_language_overrides();
    }

    #[test]
    fn dictionary_parses() {
        // Must stay a valid string-to-string map with no empty entries.
        //
        // The emptiness check is load-bearing: `dictionary()` falls back to an
        // empty map when the JSON does not deserialize into the expected
        // shape, and an empty map satisfies the loop below without running a
        // single assertion.
        let dictionary = dictionary();
        assert!(
            !dictionary.is_empty(),
            "zh-CN.json did not deserialize into a dictionary"
        );
        for (source, translation) in dictionary {
            assert!(!source.is_empty());
            assert!(!translation.is_empty());
        }
    }

    #[test]
    fn dictionary_keeps_placeholders() {
        let mut mismatches = Vec::new();
        for (source, translation) in dictionary() {
            let mut expected = placeholders(source);
            let mut actual = placeholders(translation);
            expected.sort();
            actual.sort();
            if expected != actual {
                mismatches.push(source.clone());
            }
        }
        assert!(
            mismatches.is_empty(),
            "translations dropping placeholders: {mismatches:?}"
        );
    }

    #[test]
    fn falls_back_to_english() {
        let _guard = TEST_LOCK.lock().unwrap();
        set_language(Language::English);
        assert_eq!(t("Open Settings"), "Open Settings");
        // Missing keys fall back even when Chinese is active.
        set_language(Language::SimplifiedChinese);
        assert_eq!(t("No Such Translation Key"), "No Such Translation Key");
        assert_eq!(
            localized_action_name("no_such::Action", "no such: action"),
            "no such: action"
        );
        clear_language_overrides();
    }

    #[test]
    fn actions_dictionary_parses() {
        // Guard against malformed JSON and non-string entries.
        assert!(
            !actions_dictionary().is_empty(),
            "actions-zh-CN.json did not deserialize into a dictionary"
        );
        for (action_id, translation) in actions_dictionary() {
            assert!(action_id.contains("::"), "{action_id} is not an action ID");
            assert!(!translation.is_empty());
        }
    }
}
