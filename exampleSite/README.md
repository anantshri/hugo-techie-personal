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
- **Timeline entries** with different activity types (talks, tools, articles, awards)
- **Project pages** showing active, completed, and discontinued projects
- **Gadget reviews** with various device statuses and categories

### Theme Features Demonstrated
- **Professional badge integration** - Credly and Accredible badge display with API integration
- **Responsive design** with mobile-first approach
- **Activity-based filtering** for timeline content
- **Notice/admonition system** with multiple types (info, warning, tip, note)
- **Work-in-progress notifications** for sections and pages
- **Navigation system** with breadcrumbs and prev/next
- **OEmbed support** for external content embedding (YouTube, Vimeo, SlideShare, Noti.st)
- **AI summary disclaimer** system for AI-generated content
- **Configurable analytics** (Plausible, Google Analytics, custom)
- **Image shortcodes** for optimized image handling

### Configuration Examples
The `config.toml` file demonstrates:
- **Complete theme configuration** with all available options
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
