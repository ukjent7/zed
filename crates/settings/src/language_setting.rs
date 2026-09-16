use crate::{self as settings, settings_content::LanguageContent};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use settings::{RegisterSetting, Settings};

/// Language of Zed's user interface (GUI labels only).
///
/// Default: system
#[derive(
    Copy, Clone, Debug, Serialize, Deserialize, JsonSchema, PartialEq, Eq, Default, RegisterSetting,
)]
pub enum LanguageSetting {
    #[default]
    System,
    English,
    SimplifiedChinese,
}

impl From<LanguageContent> for LanguageSetting {
    fn from(value: LanguageContent) -> Self {
        match value {
            LanguageContent::System => Self::System,
            LanguageContent::English => Self::English,
            LanguageContent::SimplifiedChinese => Self::SimplifiedChinese,
        }
    }
}

impl From<LanguageSetting> for locale::Language {
    fn from(value: LanguageSetting) -> Self {
        match value {
            LanguageSetting::System => Self::System,
            LanguageSetting::English => Self::English,
            LanguageSetting::SimplifiedChinese => Self::SimplifiedChinese,
        }
    }
}

impl Settings for LanguageSetting {
    fn from_settings(content: &crate::settings_content::SettingsContent) -> Self {
        let language: Self = content.language.unwrap_or_default().into();
        // The settings layer is the only place that feeds the UI language to
        // `locale`, so it is what makes the setting take effect immediately
        // across all UI surfaces and triggers menu bar reloads. An explicit
        // override (tests pinning English) is left untouched.
        locale::sync_language(language.into());
        language
    }
}
