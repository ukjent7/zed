//! UI language support for Zed's Simplified Chinese localization.
//!
//! GUI labels only: never use this crate for model prompts, tool schemas,
//! protocol fields, telemetry names, or anything else observed by AI models.
//! See `assets/locales/SCHEMA.md` for the dictionary format and
//! `assets/locales/GLOSSARY.md` for terminology.

use std::sync::{OnceLock, RwLock};

use collections::HashMap;
use gpui_shared_string::SharedString;

/// Dictionary compiled in from `assets/locales/zh-CN.json`.
const DEFAULT_DICTIONARY_JSON: &str = include_str!("../../../assets/locales/zh-CN.json");

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

impl Language {
    /// Parse the `language` setting value (`system` | `en` | `zh-CN`).
    /// Unknown values fall back to following the system locale.
    pub fn from_setting(value: &str) -> Self {
        match value {
            "en" => Self::English,
            "zh-CN" | "zh_CN" | "zh" => Self::SimplifiedChinese,
            _ => Self::System,
        }
    }

    /// Serialize back to the `language` setting value.
    pub fn as_setting(self) -> &'static str {
        match self {
            Self::System => "system",
            Self::English => "en",
            Self::SimplifiedChinese => "zh-CN",
        }
    }
}

/// Explicit override set via [`set_language`]; `None` follows the setting.
static LANGUAGE_OVERRIDE: RwLock<Option<Language>> = RwLock::new(None);

fn dictionary() -> &'static HashMap<String, String> {
    static DICTIONARY: OnceLock<HashMap<String, String>> = OnceLock::new();
    DICTIONARY.get_or_init(|| serde_json::from_str(DEFAULT_DICTIONARY_JSON).unwrap_or_default())
}

fn language_override() -> Option<Language> {
    LANGUAGE_OVERRIDE.read().ok().and_then(|guard| *guard)
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

/// Resolve the effective language: the explicit override when set, otherwise
/// the given setting, with [`Language::System`] following the OS locale.
pub fn resolve_language(setting: Language) -> Language {
    match language_override().unwrap_or(setting) {
        Language::System => {
            let system_locale = sys_locale::get_locale().unwrap_or_else(|| String::from("en-US"));
            if is_chinese_locale(&system_locale) {
                Language::SimplifiedChinese
            } else {
                Language::English
            }
        }
        language => language,
    }
}

/// Whether the UI should currently render Simplified Chinese.
pub fn use_chinese() -> bool {
    resolve_language(Language::System) == Language::SimplifiedChinese
}

/// Override the UI language (wired to the `language` setting later).
/// Takes effect immediately; callers re-render on the next frame.
pub fn set_language(language: Language) {
    if let Ok(mut guard) = LANGUAGE_OVERRIDE.write() {
        *guard = Some(language);
    }
}

/// Clear an override previously set with [`set_language`].
pub fn clear_language_override() {
    if let Ok(mut guard) = LANGUAGE_OVERRIDE.write() {
        *guard = None;
    }
}

/// Translate a GUI label, falling back to the English source text when
/// Chinese is not active or no translation exists. Never panics.
pub fn t(key: &str) -> SharedString {
    if !use_chinese() {
        return SharedString::from(key);
    }
    dictionary()
        .get(key)
        .map(SharedString::from)
        .unwrap_or_else(|| SharedString::from(key))
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

    // `LANGUAGE_OVERRIDE` is process-global; serialize tests that mutate it.
    static TEST_LOCK: Mutex<()> = Mutex::new(());

    #[test]
    fn language_setting_round_trip() {
        assert_eq!(Language::from_setting("system"), Language::System);
        assert_eq!(Language::from_setting("en"), Language::English);
        assert_eq!(Language::from_setting("zh-CN"), Language::SimplifiedChinese);
        assert_eq!(Language::from_setting("unexpected"), Language::System);
        assert_eq!(Language::System.as_setting(), "system");
        assert_eq!(Language::English.as_setting(), "en");
        assert_eq!(Language::SimplifiedChinese.as_setting(), "zh-CN");
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
    fn dictionary_parses() {
        // Empty today (PR-1 skeleton); must stay a valid string-to-string map.
        let dictionary = dictionary();
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
        clear_language_override();
    }
}
