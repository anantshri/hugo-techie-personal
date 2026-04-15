# Changelog

All notable changes to the Hugo Techie Personal theme will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2026-04-15

### Added
- **Custom CSS support** — Load additional stylesheets via `params.custom_css` list in site config
- **Custom JS support** — Load additional scripts via `params.custom_js` list in site config (loaded before `</body>`)
- **Custom font overrides** — Override theme fonts via `[params.fonts]` config section (CSP-safe, no inline styles)
  - `google_fonts_url` — Load a custom Google Fonts stylesheet
  - `family_sans`, `family_serif`, `family_mono` — Override CSS custom properties for font families
  - Uses Hugo's `resources.FromString` to generate an external fingerprinted CSS file

### Changed
- **Partial restructuring for site-level overrides:**
  - Moved theme `<head>` content (favicons, analytics, slides OG/OEmbed/Schema.org) from `head_custom.html` into `header.html`
  - `head_custom.html` is now an empty hook — site owners can override it in their `layouts/partials/` to inject custom `<head>` content
  - `foot_custom.html` is now shipped as an empty hook in the theme — site owners can override it to inject content before `</body>`
  - Custom JS scripts load before `foot_custom.html`, giving site overrides access to any custom libraries

## [2.0.1] - 2026-04-15

### Fixed
- Fixed exampleSite `config.toml` configuration errors that caused build failures on sites using the example as a starting point

## [2.0.0] - 2026-04-15

### Added
- **Slides / Presentations system** — Self-hosted PDF presentation viewer with interactive navigation
  - PDF-to-WebP slide processing pipeline (`process-slides.sh`, `scaffold-slides.sh`)
  - Full interactive viewer with keyboard/touch navigation, grid overview, fullscreen, PDF download
  - OEmbed discovery support — slides are embeddable on any site via standard OEmbed protocol
  - Iframe-embeddable viewer output (`embed.html`) per presentation
  - `slideviewer` shortcode for native same-site slide embedding (no iframe)
  - `slide-embed` shortcode for card-style links to presentations
  - Slides archetype (`archetypes/slides.md`) for quick scaffolding via `hugo new`
  - Hugo image processing: single high-res WebP per slide in `assets/`, resized to thumb/medium/full at build time
  - Configurable viewer: theme, toolbar buttons, preloading, keyboard/swipe toggle
  - Slides listing page with year-based grouping
- **Events map** — Leaflet-based map showing physical event locations
  - Combines locations from both slides and timeline entries
  - Marker clustering for dense areas
  - `LocationsJSON` and `SlidesJSON` output formats feed the map data
  - `online: true` frontmatter flag to exclude virtual events from the map
  - Standalone map page support (`layout: map`)
- **Social chatter** — Embedded social media posts on timeline entry pages
  - Supports Twitter/X, Bluesky, Mastodon, LinkedIn, Facebook, Instagram
  - Platform auto-detected from URL; no JavaScript required
  - Uses OEmbed system for Twitter/X, Bluesky, Mastodon; direct iframes for others
- **Related links** — Card-style blocks on timeline entries linking to blogs, research pages, etc.
  - Auto-fetches Open Graph metadata (title, image, description) when omitted
- **Noti.st migration script** (`scripts/migrate-notist.py`) — Import existing Noti.st presentations
- **Slides migration script** (`scripts/migrate-slides.sh`) — Move legacy bundle PDFs to new inbox workflow
- **Documentation** — Added `docs/` directory with detailed reference guides:
  - `docs/configuration.md` — Complete `config.toml` parameter reference
  - `docs/layouts.md` — Bio page, Map page, Home page, alternate list layouts, Banner
  - `docs/shortcodes.md` — All shortcodes with usage examples
- **Example site content** — Added missing examples:
  - Timeline entries for all activity types: `discussion`, `whitepaper`, `quote`, `curator`
  - Timeline entries with `location` coordinates, `social_chatter`, `related_links`, `online: true`
  - Interests section with example pages
  - Bio page demonstrating the biography layout
  - Events map standalone page
  - AI summary example in `ai_summary/unified/`

### Changed
- **BREAKING**: Minimum Hugo version requirement updated from 0.18 to 0.158.0 (required for `.Site.Language.Locale` support)
- **BREAKING**: Slide PDFs now live in `assets/slides/pdf_files/` inbox instead of content bundles; `process-slides.sh` copies them to `static/slides/<slug>/slides.pdf` for download
- **CI Improvement**: Workflow now dynamically extracts minimum Hugo version from `theme.toml`
- **Security**: Implemented job-level permissions instead of workflow-level write access
- **Security**: Reduced `build-and-prepare` job permissions (removed unnecessary `pages:write`)
- Updated documentation to reflect new Hugo version requirement
- All CSS and JS assets now minified via Hugo Pipes (`| minify`) before fingerprinting
- Styled 404 page with proper heading and back-to-home link
- Added LICENSE file for vendored Leaflet and Leaflet.markercluster libraries
- Deduplicated OEmbed logic: shortcode is now a thin wrapper around `partials/oembed.html`
- Added `-webkit-backdrop-filter` prefix for older Safari compatibility
- Added missing `allow` iframe attribute to shortcode OEmbed output (was only in partial)
- Added same-site slides rendering to partial OEmbed (was only in shortcode)

### Removed
- Removed legacy `list_old.html` layout
- Removed empty `layouts/badges/` directory

### Fixed
- Fixed empty `canonical` and `og:url` meta tags — now correctly use page permalink
- Fixed `og:title` and `og:description` meta tags to use page-specific values instead of site-wide defaults
- Fixed hardcoded `article:modified_time` (was stuck at 2021-05-24) — now uses page `.Lastmod`
- Fixed `og:image` emitting broken URL when page has no `featured_image`
- Fixed hardcoded "2 minutes" reading time — now uses Hugo's computed `.ReadingTime`
- Fixed duplicate Google Fonts loading (Inter/Merriweather loaded in `<head>` but unused; JetBrains Mono loaded twice)
- Added missing Leaflet marker images (`marker-icon.png`, `marker-icon-2x.png`, `marker-shadow.png`) for events map
- Fixed compatibility issues with Hugo versions below 0.141.0 due to `try` function usage
- Fixed CI HTML validation false positives (CSS color codes containing "404" no longer trigger errors)
- Fixed GitHub Actions release notification script (now updates release description instead of creating invalid comments)
- Fixed badge template error in `manual-badges.html` (added proper type checking and nil safety)
- Fixed incorrect icon path in README (`themes/anantshri/` → `themes/hugo-techie-personal/`)
- Fixed `banner` → `Banner` parameter name in exampleSite config to match template expectation
- Updated exampleSite README to accurately describe demonstrated features

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
