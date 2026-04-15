# Hugo Techie Personal - Example Site

This is a complete example site demonstrating the Hugo Techie Personal theme features and configuration options.

## Quick Start

1. **Install Hugo** (version 0.141.0 or later)
2. **Clone or download** this example site
3. **Run the development server**:
   ```bash
   hugo server -D
   ```
4. **Open your browser** to `http://localhost:1313`

## What's Included

### Content Examples
- **Timeline entries** covering all activity types (talk, training, tool, panel, discussion, whitepaper, article, quote, recognition, ctf, curator)
- **Slide presentations** with interactive viewer, OEmbed support, and embeddable iframes
- **Project pages** showing active, completed, discontinued, and planned projects
- **Gadget reviews** with various device statuses and categories
- **Interests** section with personal interest pages
- **Bio page** demonstrating the biography layout with copy-to-clipboard and format tabs
- **Events map** standalone page with timeline and slide locations
- **AI summary** example (auto-included from `ai_summary/unified/`)

### Theme Features Demonstrated
- **Self-hosted slides/presentations** — Interactive PDF slide viewer with keyboard/touch navigation
- **OEmbed & embeddable slides** — Each presentation has OEmbed discovery and an iframe-embeddable viewer
- **Events map** — Leaflet-based map with locations from slides and timeline entries
- **Bio page** — Structured biography with Rendered/Markdown/Plain Text tabs and copy button
- **Social chatter** — Embedded social media posts on timeline entry pages
- **Related links** — Card-style blocks linking to blogs, research, and external content
- **Professional badge integration** — Credly and Accredible badge display with API integration
- **Responsive design** with mobile-first approach
- **All activity types** — talk, training, tool, panel, discussion, whitepaper, article, quote, recognition, ctf, curator
- **Notice/admonition system** with multiple types (info, warning, tip, note)
- **Work-in-progress notifications** for sections and pages
- **Navigation system** with breadcrumbs and prev/next
- **OEmbed support** for external content embedding (YouTube, Vimeo, and more)
- **AI summary** — Auto-included from `ai_summary/` directory
- **Location coordinates** — Timeline entries with lat/lng for the events map
- **Online events** — `online: true` flag to exclude virtual events from the map
- **Configurable analytics** (Plausible, Google Analytics, custom)

### Configuration Examples
The `config.toml` file demonstrates:
- **Theme configuration** with commonly used options
- **Slides/presentations module** with viewer, map, and OEmbed settings
- **Output formats** for OEmbed, Embed, SlidesJSON, and LocationsJSON
- **Social media integration** with verification links
- **Analytics setup** for privacy-focused tracking
- **Navigation customization** and internationalization
- **Work-in-progress system** configuration
- **Timeline and activity settings**

## Customization

### Replace Sample Content
1. **Update `content/_index.md`** with your personal information
2. **Replace timeline entries** in `content/timeline/` with your activities
3. **Add your projects** to `content/projects/` with appropriate status
4. **Create gadget reviews** in `content/gadget/` for your devices
5. **Add interests** in `content/interests/` for personal interest pages
6. **Update `content/bio.md`** with your biography and photos
7. **Add AI summaries** in `ai_summary/unified/` for timeline entries

### Update Configuration
1. **Modify `config.toml`** with your site details and preferences
2. **Update social links** in the home page front matter
3. **Configure analytics** with your tracking preferences
4. **Customize navigation labels** for internationalization
5. **Set up work-in-progress** notifications as needed

### Replace Assets
1. **Replace the placeholder profile image** in `assets/images/profile.png`
   - The example site includes a generic placeholder image
   - Replace with your own profile photo (PNG, JPG, or WebP format)
   - The theme will automatically resize images for different screen sizes
2. **Add project screenshots** in `assets/images/projects/`
   - Projects without specific images will show a generic project placeholder
   - Name your project images to match the project file name (e.g., `my-project.png` for `my-project.md`)
3. **Add gadget photos** for device reviews in `assets/images/gadget/`
   - Gadgets without specific images will show a generic gadget placeholder
   - Name your gadget images to match the gadget file name (e.g., `macbook-pro.png` for `macbook-pro.md`)
4. **Create custom favicons** in `static/` directory

## Theme Features

### Activity Icons
The theme includes comprehensive activity icons:
- **Built-in icons** for common activities (talk, tool, training, etc.)
- **Social media icons** (Twitter, LinkedIn, Mastodon, GitHub)
- **Notice system icons** (info, warning, tip, note)
- **Fallback system** with text badges if icons are missing

### Placeholder Images
The theme includes automatic placeholder images for better visual consistency:
- **Project placeholder** - Generic folder icon for projects without specific images
- **Gadget placeholder** - Generic device icon for gadgets without specific images
- **Timeline placeholder** - Generic timeline icon for timeline entries with missing featured images
- **Automatic fallback** - Placeholders appear when no matching image is found
- **Visual consistency** - Maintains layout integrity across all content types

### Notice System
Use notices to highlight important information:
```hugo
{{< notice info "Custom Title" >}}
Your notice content here
{{< /notice >}}
```

Available types: `info`, `warning`, `tip`, `note`

### OEmbed Support
Embed external content easily:
```hugo
{{< oembed url="https://www.youtube.com/watch?v=example" >}}
```

Supports: YouTube, Vimeo, Twitter, Spotify, and more

### FontAwesome Icons
Include FontAwesome icons inline:
```hugo
{{< fontawesome "heart" >}} Love this feature!
```

## Development

### Local Development
```bash
# Start development server
hugo server -D

# Build for production
hugo --minify
```

### Content Creation
- **Timeline entries**: Use `hugo new timeline/YYYY-MM-DD-title.md`
- **Presentations**: Drop PDF in `assets/slides/pdf_files/`, run `scaffold-slides.sh`, then `process-slides.sh`
- **Projects**: Use `hugo new projects/project-name.md`
- **Gadgets**: Use `hugo new gadget/device-name.md`

## Support

For theme support and documentation:
- **Theme Documentation**: See the main theme README
- **GitHub Issues**: Report bugs and request features
- **Community**: Join discussions and share experiences

## License

This example site content is provided as a starting point for your own site. Feel free to modify, replace, and customize all content to match your needs.

The Hugo Techie Personal theme itself is licensed under the MIT License.
