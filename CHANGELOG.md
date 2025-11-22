# Changelog

All notable changes to the Hugo Techie Personal theme will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **BREAKING**: Minimum Hugo version requirement updated from 0.18 to 0.141.0
- **CI Improvement**: Workflow now dynamically extracts minimum Hugo version from `theme.toml`
- Updated documentation to reflect new Hugo version requirement

### Fixed
- Fixed compatibility issues with Hugo versions below 0.141.0 due to `try` function usage
- Fixed CI HTML validation false positives (CSS color codes containing "404" no longer trigger errors)
- Fixed GitHub Actions release notification script (now updates release description instead of creating invalid comments)

## [1.1.0] - 2024-12-28

### Added
- **Professional Badge Integration** - Comprehensive support for certification badges
- **Credly Integration** - Automatic badge fetching from Credly API with caching
- **Accredible Integration** - Credential display from Accredible platform
- **Unified Badge System** - Display badges from multiple platforms in single grid
- **Badge Caching System** - Intelligent API caching for improved performance
- **Badge Expiration Handling** - Show/hide expired badges with visual indicators
- **Badge Shortcodes** - `{{< badges >}}`, `{{< credly-badges >}}`, `{{< accredible-badges >}}`
- **Badge Filtering Options** - Size control, expiration filtering, platform selection
- **Local Image Caching** - Automatic badge image caching for faster loads
- **Fallback System** - API → cached data → Site.Data → graceful degradation

### Features
- **Badge API Integration**: Automatic fetching from Credly and Accredible APIs
- **Smart Caching**: Reduces API calls and improves site performance
- **Responsive Badge Display**: Adapts to different screen sizes and layouts
- **Badge Expiration Management**: Visual indicators and filtering for expired badges
- **Multi-platform Support**: Unified display of badges from different providers
- **Error Handling**: Graceful fallbacks when badge APIs are unavailable

## [1.0.0] - 2024-09-28

### Added
- **Timeline-based content organization** with activity categorization
- **Responsive design** with mobile-first approach and hamburger menu
- **Activity icons system** with 25+ built-in SVG icons and fallback support
- **Notice/admonition system** with 4 types (info, warning, tip, note)
- **Enhanced OEmbed support** for YouTube, Vimeo, Twitter, Spotify, and more
- **Work-in-progress notification system** with configurable messages
- **Modern navigation system** with breadcrumbs and prev/next navigation
- **Flexible analytics configuration** (Plausible, Google Analytics, custom)
- **Social media integration** with verification link support
- **FontAwesome shortcode** for inline SVG icons
- **Configurable navigation labels** for internationalization
- **Status message system** for discontinued/upcoming content
- **Privacy-enhanced YouTube embedding** with nocookie domains
- **Lazy loading** for embedded content
- **Comprehensive error handling** and graceful fallbacks
- **Complete example site** with sample content demonstrating all features

### Features
- **Activity types**: talk, tool, training, article, recognition, award, and more
- **Content sections**: timeline, projects, gadgets, interests
- **Project status tracking**: active, completed, discontinued
- **Device status tracking**: active, upcoming, discontinued
- **Hierarchical icon system**: site icons override theme icons
- **Responsive breakpoints**: 576px, 767px, 768px, 992px, 1100px, 1200px
- **Semantic HTML5** with proper accessibility support
- **Performance optimized** with minified CSS and optimized assets

### Technical
- **Hugo compatibility**: 0.141.0+
- **Template engine**: Go templates with advanced logic
- **CSS framework**: Custom responsive CSS with Grid and Flexbox
- **Icon format**: SVG for scalability and performance
- **Configuration**: Extensive TOML-based configuration options

### Documentation
- **Comprehensive README** with installation and configuration guides
- **Example site** with sample content and configuration
- **Configuration documentation** for all theme parameters
- **Usage guides** for content creation and customization
- **Icon system documentation** with requirements and fallback behavior

### Based On
- Extended from [Hugo Xmin](https://github.com/yihui/hugo-xmin) by Yihui Xie
- Maintains minimal philosophy while adding powerful timeline functionality
- Preserves clean, readable code structure with extensive customization options
