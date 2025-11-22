---
title: Badges
---

This page demonstrates the badge integration feature of the Hugo Techie Personal theme. The theme supports displaying professional certifications and badges from Credly and Accredible platforms.

## Badge Display Options

The theme supports three badge sizes:

### Normal Size (Default - 250x250px)

{{< badges size="normal" >}}

### Big Size (500x500px)

{{< badges size="big" >}}

### Small Size (64x64px - Icon Only)

{{< badges size="small" >}}

## Configuration

To display your own badges, configure your `config.toml`:

```toml
[params]
  # Credly badge integration
  credly_username = "your-credly-username"
  credly_image_dir = "images/CredlyBadges"
  
  # Accredible badge integration
  accredible_username = "your-accredible-username"
  accredible_image_dir = "images/AccredibleBadges"
```

## Features

- **Automatic API fetching** from Credly and Accredible
- **Intelligent caching** of badge data and images
- **Expired badge handling** with visual indicators
- **Multiple display sizes** (small, normal, big)
- **Responsive grid layout** that adapts to screen size
- **Tooltip support** showing badge descriptions on hover
- **Flexible filtering** options (show/hide expired badges)

## Usage Examples


### Display all badges (normal size)
```
{{< badges >}}
```
{{< badges >}}

### Display big badges
```
{{< badges size="big" >}}
```
{{< badges size="big" >}}

###  Display small badges
```
{{< badges size="small" >}}
```
{{< badges size="small" >}}

###  Hide expired badges 
```
{{< badges hide_expired="true" >}}
```
{{< badges hide_expired="true" >}}

###  Show only expired badges 
```
{{< badges show_expired="true" >}}
```
{{< badges show_expired="true" >}}

###  Display only Credly badges 
```
{{< badges show_accredible="false" >}}
```
{{< badges show_accredible="false" >}}

### Display only Accredible badges 
```
{{< badges show_credly="false" >}}
```
{{< badges show_credly="false" >}}


{{< notice info "Note" >}}
This demo site doesn't have actual badge credentials configured. In a real implementation, you would add your Credly and/or Accredible usernames to the config.toml file to display your actual badges.
{{< /notice >}}

