# Contributing to Hugo Techie Personal

Thank you for your interest in contributing to Hugo Techie Personal! This document provides guidelines for contributing to the theme.

## Ways to Contribute

### 🐛 Bug Reports
- Use the GitHub issue tracker to report bugs
- Include Hugo version, theme version, and steps to reproduce
- Provide minimal example configuration if possible

### 💡 Feature Requests
- Discuss new features in GitHub issues before implementing
- Consider if the feature aligns with the theme's minimal philosophy
- Provide use cases and examples of how the feature would be used

### 📝 Documentation
- Improve README.md, configuration examples, or code comments
- Add or improve example content in the exampleSite
- Help with internationalization of navigation labels

### 🔧 Code Contributions
- Follow the existing code style and structure
- Test changes with the included exampleSite
- Ensure responsive design works across different screen sizes
- Maintain accessibility standards

## Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/yourusername/hugo-techie-personal.git
   cd hugo-techie-personal
   ```
3. **Test with example site**:
   ```bash
   cd exampleSite
   hugo server -D
   ```

## Code Guidelines

### HTML Templates
- Use semantic HTML5 elements
- Include proper ARIA labels for accessibility
- Handle both string and array values for activity/focus parameters
- Provide fallbacks for missing data or assets

### CSS
- Follow mobile-first responsive design principles
- Use CSS Grid and Flexbox for layouts
- Maintain existing breakpoints: 576px, 767px, 768px, 992px, 1100px, 1200px
- Keep styles organized and well-commented

### Configuration
- Document all new configuration options in README.md
- Provide sensible defaults for all parameters
- Include examples in exampleSite/config.toml

### Icons and Assets
- Use SVG format for all icons
- Provide fallback behavior for missing icons
- Follow naming conventions: `{activity-name}.svg`, `{platform}.svg`
- Optimize SVG files for size and accessibility

## Testing

### Required Tests
- [ ] Theme builds successfully with Hugo 0.18+
- [ ] ExampleSite generates without errors
- [ ] Responsive design works on mobile, tablet, and desktop
- [ ] All configuration options work as documented
- [ ] Activity icons display correctly with fallbacks
- [ ] Navigation system works properly
- [ ] OEmbed embeds work for supported platforms

### Browser Testing
- Test on modern browsers (Chrome, Firefox, Safari, Edge)
- Verify mobile responsiveness
- Check accessibility with screen readers

## Submission Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Make your changes** following the guidelines above
3. **Test thoroughly** with the exampleSite
4. **Commit with clear messages**:
   ```bash
   git commit -m "Add: Brief description of changes"
   ```
5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Create a Pull Request** with:
   - Clear description of changes
   - Screenshots for UI changes
   - Testing steps performed
   - Any breaking changes noted

## Code of Conduct

### Our Standards
- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers learn and contribute
- Maintain a welcoming environment for all contributors

### Scope
This Code of Conduct applies to all project spaces, including:
- GitHub repository (issues, pull requests, discussions)
- Documentation and example content
- Any other project-related communication

## Questions?

- **General questions**: Open a GitHub issue with the "question" label
- **Security issues**: Email the maintainer directly (see README.md)
- **Feature discussions**: Use GitHub discussions or issues

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- CHANGELOG.md for significant contributions
- README.md acknowledgments section (for major contributions)

Thank you for helping make Hugo Techie Personal better for the tech community! 🚀
