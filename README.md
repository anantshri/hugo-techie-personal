# Hugo Techie Personal

A timeline-based personal site theme designed specifically for tech professionals who love to share their work, projects, and journey with the community.

[![Hugo](https://img.shields.io/badge/hugo-0.141.0+-blue.svg)](https://gohugo.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

✨ **Timeline-based content organization** - Perfect for showcasing your professional journey  
🎯 **Activity categorization** - Organize content by talks, tools, articles, training, and more  
🏆 **Professional badge integration** - Display Credly and Accredible certifications with API integration  
📱 **Responsive design** - Mobile-first approach with modern CSS Grid and Flexbox  
🔧 **Highly configurable** - Extensive customization options via config.toml  
🎨 **Notice system** - Beautiful callout boxes for important information  
🔗 **OEmbed support** - Embed YouTube, Vimeo, Twitter, and more  
🌐 **Social integration** - Built-in social media links with verification support  
📊 **Analytics ready** - Supports Plausible, Google Analytics, and custom solutions  
♿ **Accessible** - Semantic HTML5 with proper ARIA labels  
🚀 **Performance optimized** - Minimal CSS, lazy loading, and optimized assets

## Perfect For

- **Tech professionals** building their personal brand
- **Certified professionals** showcasing credentials and achievements
- **Open source contributors** showcasing their projects  
- **Developers and security researchers** sharing their journey
- **Conference speakers** documenting talks and presentations
- **Technology enthusiasts** reviewing gadgets and tools

## Quick Start

1. **Install Hugo** (version 0.141.0 or later)
2. **Create a new site**:
   ```bash
   hugo new site my-techie-site
   cd my-techie-site
   ```
3. **Add the theme**:
   ```bash
   git submodule add https://github.com/anantshri/hugo-techie-personal.git themes/hugo-techie-personal
   ```
4. **Copy example configuration**:
   ```bash
   cp themes/hugo-techie-personal/exampleSite/config.toml .
   ```
5. **Start the development server**:
   ```bash
   hugo server -D
   ```

## Demo

**Live Example:** See the theme in action at **[anantshri.info](https://anantshri.info)** - the author's personal site showcasing real-world usage with extensive timeline content, project portfolios, and gadget reviews.

**Demo Site:** A live demo is automatically deployed to GitHub Pages with each release, showcasing all theme features and the latest updates.

**Example Site:** Check out the [example site](exampleSite/) included with the theme to see all features and configuration options.

---

## Acknowledgments

This theme extends the excellent [Hugo Xmin](https://github.com/yihui/hugo-xmin) theme by [Yihui Xie](https://yihui.org), maintaining its minimal philosophy while adding powerful timeline functionality and modern features.

## Configuration

This theme provides comprehensive timeline functionality and additional features:

### Noti.st Integration

The theme supports embedding slides from Noti.st, including custom domain CNAMEs. Configure this in your `config.toml`:

```toml
[params]
  # Your Noti.st username
  notist_username = "your-username"
  
  # Array of custom domains that point to Noti.st
  # This allows the theme to recognize your custom domain as a Noti.st embed
  notist_custom_domains = ["slides.yourdomain.com", "presentations.example.org"]
```

**Example:**
- If you have `slides.anantshri.info` as a CNAME pointing to Noti.st
- Add it to the `notist_custom_domains` array
- The theme will automatically embed slides from that domain using your `notist_username`

### Analytics Configuration

The theme supports multiple analytics providers with flexible configuration:

```toml
[params.analytics]
  provider = "plausible"           # Options: "plausible", "plausible_cloud", "google", "custom"
  domain = "yourdomain.com"        # Your domain for analytics
  
  # For self-hosted Plausible with custom proxy (like nginx redirect):
  api_endpoint = "/api/event"      # Custom API endpoint
  script_src = "/js/script.js"     # Custom script source
  
  # For Plausible Cloud:
  # provider = "plausible_cloud"
  # domain = "yourdomain.com"
  
  # For Google Analytics:
  # provider = "google"
  # tracking_id = "G-XXXXXXXXXX"
  
  # For custom analytics code:
  # provider = "custom"
  # custom_code = '''<script>/* your custom analytics */</script>'''
```

**Self-hosted Plausible Setup:**
1. Set `provider = "plausible"`
2. Configure your nginx proxy to redirect `/api/event` and `/js/script.js` to your Plausible instance
3. Set your domain in the `domain` parameter
4. The theme will use your custom endpoints

**Note:** The nginx configuration for proxying is outside the theme scope but enables privacy-friendly analytics without exposing your analytics server directly.

### Work in Progress Notification System

The theme includes a flexible system for displaying work-in-progress notifications:

```toml
[params.work_in_progress]
  enabled = true                   # Enable/disable globally
  default_message = "This content is currently being updated..."
  default_title = "🚧 Work in Progress"
  exclude_statuses = ["discontinued", "archived", "completed", "finished"]  # Don't show WIP for these statuses
  
  # Predefined message types
  [params.work_in_progress.types]
    updating = { title = "🚧 Work in Progress", message = "Content being updated..." }
    incomplete = { title = "📝 Content Incomplete", message = "Partial information available..." }
    review = { title = "🔍 Under Review", message = "Content under review..." }
    placeholder = { title = "📋 Placeholder", message = "Content coming soon..." }
```

**Usage Options:**

1. **Section-level**: Add to section's `_index.md`:
   ```yaml
   work_in_progress: "updating"  # Use predefined type
   # OR
   work_in_progress: true        # Use default message
   # OR custom message:
   work_in_progress_title: "Custom Title"
   work_in_progress_message: "Custom message here"
   ```

2. **Page-level**: Add to individual page front matter (overrides section-level)
3. **Automatic display**: Shows on both list and single page views
4. **Smart exclusions**: WIP messages are automatically hidden for content with "final" statuses like `discontinued`, `archived`, `completed`, or `finished`

### Navigation System

The theme includes a modern, configurable navigation system:

```toml
[params.navigation]
  enable_breadcrumbs = true           # Enable breadcrumb navigation
  enable_prev_next = true             # Enable previous/next navigation
  breadcrumb_separator = "›"          # Breadcrumb separator character
  show_section_context = true         # Show current section in header
  
  # Configurable navigation labels (for internationalization)
  [params.navigation.labels]
    home = "Home"
    projects = "Projects"
    gadgets = "Gadgets"
    timeline = "Timeline"
    back_to = "Back to"
    previous = "Previous"
    next = "Next"
    currently_used = "Currently Used"
    upcoming = "Upcoming"
    discontinued = "Discontinued"
    discontinued_projects = "Discontinued Projects"
    archived_device = "⚠️ Archived Device"
    planned_device = "📋 Planned Device"
```

**Navigation Features:**
- **Breadcrumb navigation**: Shows `Home › Section › Current Page` path
- **Previous/Next navigation**: Navigate between adjacent pages in sections
- **Responsive design**: Adapts to mobile and desktop layouts
- **Configurable labels**: Customize all text for internationalization
- **Accessible**: Proper ARIA labels and semantic HTML

### Timeline Features

This theme is designed for timeline-based content with support for:
- Activity-based categorization
- Focus area taxonomies
- Embedded content (YouTube, Vimeo, SlideShare, Noti.st)
- Responsive timeline layout
- Configurable activity icons with intelligent fallbacks

#### Activity Icons Configuration

Configure timeline activity icons in your `config.toml`:

```toml
[params.timeline]
  show_activity_icons = true    # Enable/disable activity icons (default: true)
```

#### Icon System Architecture

The theme uses a **hierarchical icon system** that checks multiple locations:

**Theme Icons (Built-in):**
- Default icons included with theme in `themes/anantshri/assets/images/`
- Includes all standard activity icons: `talk.svg`, `tool.svg`, `training.svg`, etc.
- Social media icons: `twitter.svg`, `linkedin.svg`, `mastodon.svg`, etc.
- Notice system icons: `info.svg`, `note.svg`, `tip.svg`, `warning.svg`

**Site-Specific Icons (Optional Override):**
- Place custom icons in your site's `assets/images/` directory
- Same naming format: `{activity-name}.svg` or `{platform}.svg`
- Site icons override theme icons when present

**Icon Requirements:**
- Format: SVG files for scalability
- Activity icons: 25x25px recommended
- Social icons: 50x50px recommended
- Notice icons: Included with theme

**Fallback Behavior:**
- **First**: Checks site `assets/images/` for custom icons
- **Second**: Falls back to theme's built-in icons
- **Third**: Shows styled text badges/links if no icons found
- **Configuration**: `show_activity_icons = false` disables all icons

## New Features Added (Extracted from hugo_booster)

### Notice/Admonition System
The theme now includes a comprehensive notice system for creating styled callout boxes:

**Usage:**
```hugo
{{< notice warning >}}
This is a warning message with custom styling!
{{< /notice >}}

{{< notice info "Custom Title" >}}
This is an info box with a custom title.
{{< /notice >}}
```

**Available Types:**
- `warning` - Red warning notices
- `info` - Orange informational notices  
- `tip` - Green tip notices
- `note` - Blue note notices (default)

**Features:**
- Custom titles supported
- Light/dark mode compatible
- Responsive design
- SVG icons for each type

### FontAwesome Shortcode
Easily embed FontAwesome icons as inline SVG:

**Usage:**
```hugo
{{< fontawesome "heart" >}} Love this feature!
```

**Requirements:**
- Place FontAwesome SVG files in `static/fontawesome/` directory
- SVG files should be named like `heart.svg`, `star.svg`, etc.

### Enhanced OEmbed System
The theme includes comprehensive OEmbed support with both hardcoded and data-driven providers:

**Hardcoded Platforms:**
- YouTube (with privacy-enhanced nocookie domains)
- Vimeo
- SlideShare
- Spreaker
- Noti.st (configurable custom domains)

**Data-Driven Platforms:**
The theme includes `data/oembed.json` with additional provider configurations for:
- Twitter
- Spotify
- SpeakerDeck
- CodeSandbox
- Apple Podcasts

**Features:**
- Consistent error handling with styled fallback messages
- Lazy loading iframes for performance
- Responsive wrapper containers
- Flexible configuration via JSON data file
- Automatic fallback chain: hardcoded → data-driven → error message

**Usage:**
```hugo
<!-- As shortcode -->
{{< oembed url="https://www.youtube.com/watch?v=example" >}}

<!-- As partial -->
{{ partial "oembed.html" "https://www.youtube.com/watch?v=example" }}
```

### Professional Badge Integration

The theme provides comprehensive support for displaying professional certifications and badges from popular platforms:

#### Credly Integration

Display your Credly badges with automatic API fetching and intelligent caching:

```toml
[params]
  # Your Credly username
  credly_username = "your-username"
  
  # Optional: Custom image directory for cached badge images
  credly_image_dir = "images/CredlyBadges"  # Default
```

**Usage:**
```hugo
<!-- Display all Credly badges -->
{{< credly-badges >}}

<!-- Display with custom size -->
{{< credly-badges size="small" >}}

<!-- Hide expired badges -->
{{< credly-badges hide_expired="true" >}}

<!-- Show only expired badges -->
{{< credly-badges show_expired="true" >}}
```

#### Accredible Integration

Display your Accredible credentials with API integration:

```toml
[params]
  # Your Accredible username
  accredible_username = "your-username"
  
  # Optional: Custom image directory for cached badge images
  accredible_image_dir = "images/AccredibleBadges"  # Default
```

**Usage:**
```hugo
<!-- Display all Accredible badges -->
{{< accredible-badges >}}

<!-- Display with custom options -->
{{< accredible-badges size="small" hide_expired="true" >}}
```

#### Unified Badge Display

Display badges from both platforms in a unified grid:

```hugo
<!-- Display badges from both Credly and Accredible -->
{{< badges >}}

<!-- Display only Credly badges -->
{{< badges show_accredible="false" >}}

<!-- Display only Accredible badges -->
{{< badges show_credly="false" >}}

<!-- Custom sizing and filtering -->
{{< badges size="small" hide_expired="true" >}}
```

**Badge Features:**
- **Automatic API fetching** with intelligent caching for performance
- **Fallback system**: API → cached data → Site.Data → graceful degradation
- **Expiration handling**: Show/hide expired badges with visual indicators
- **Responsive design**: Adapts to different screen sizes
- **Local image caching**: Reduces API calls and improves load times
- **Error handling**: Graceful fallbacks when APIs are unavailable
- **Unified display**: Mix badges from multiple platforms seamlessly

## Automated Deployment

The theme includes GitHub Actions for automated testing and demo site deployment:

- **Continuous Testing** - Automatic theme validation on every push and pull request
- **Demo Deployment** - Automatic GitHub Pages deployment on new releases
- **Multi-version Testing** - Tests against multiple Hugo versions for compatibility
- **HTML Validation** - Automated checks for generated content quality

The demo site is automatically updated whenever a new release is published, ensuring the latest features are always showcased.
