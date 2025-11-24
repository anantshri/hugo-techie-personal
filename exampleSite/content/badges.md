---
title: Badges
---

This page demonstrates the badge integration feature of the Hugo Techie Personal theme. The theme supports displaying professional certifications and badges from multiple platforms:

- **Credly** - Popular badge platform with API integration
- **Accredible** - Professional credential management platform
- **Badgr** - Open Badges platform with API support
- **Bugcrowd** - Bug bounty platform badges and achievements
- **HackerOne** - Bug bounty platform badges and achievements
- **Open Badges** - Standards-based badges (JSON-LD format)
- **Manual/Custom Badges** - User-defined badges via data files

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
  
  # Badgr badge integration (optional)
  badgr_username = "your-badgr-username"
  badgr_api_token = "your-api-token"  # Required for API access
  badgr_image_dir = "images/BadgrBadges"
  
  # Bugcrowd badge integration (optional)
  bugcrowd_username = "your-bugcrowd-username"
  bugcrowd_image_dir = "images/BugcrowdBadges"
  
  # HackerOne badge integration (optional)
  hackerone_username = "your-hackerone-username"
  hackerone_image_dir = "images/HackerOneBadges"
```

### Manual Badges

Add custom badges by creating `data/ManualBadges.json`:

```json
{
  "badges": [
    {
      "id": "custom-1",
      "name": "Custom Badge Name",
      "description": "Badge description",
      "image_url": "https://example.com/badge-image.png",
      "issued_at": "2024-01-15T00:00:00Z",
      "expires_at": "2025-01-15T00:00:00Z",  # Optional
      "url": "https://example.com/badge-link"
    }
  ]
}
```

### Open Badges

Add Open Badges (JSON-LD format) by creating `data/OpenBadges.json`:

```json
{
  "badges": [
    {
      "@context": "https://w3id.org/openbadges/v2",
      "type": "Assertion",
      "id": "https://example.com/badges/badge-1",
      "badge": {
        "type": "BadgeClass",
        "name": "Badge Name",
        "description": "Badge description",
        "image": "https://example.com/badge-image.png"
      },
      "issuedOn": "2024-01-15T00:00:00Z",
      "url": "https://example.com/badge-link"
    }
  ]
}
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

### Display only Manual badges
```
{{< badges show_credly="false" show_accredible="false" show_openbadges="false" show_badgr="false" >}}
```
{{< badges show_credly="false" show_accredible="false" show_openbadges="false" show_badgr="false" >}}

### Display only Open Badges
```
{{< openbadges-badges >}}
```
{{< openbadges-badges >}}

### Display only Badgr badges
```
{{< badgr-badges >}}
```
{{< badgr-badges >}}

### Display only Bugcrowd badges
```
{{< bugcrowd-badges >}}
```
{{< bugcrowd-badges >}}

### Display only HackerOne badges
```
{{< hackerone-badges >}}
```
{{< hackerone-badges >}}

### Display Bugcrowd badges with statistics and hall of fame
```
{{< bugcrowd-badges show_statistics="true" show_hall_of_fame="true" >}}
```
{{< notice info "Note" >}}
Bugcrowd integration automatically fetches and caches performance statistics and hall of fame data, but only displays awarded badges by default. Use `show_statistics="true"` and `show_hall_of_fame="true"` to display additional information.
{{< /notice >}}


{{< notice info "Note" >}}
This demo site doesn't have actual badge credentials configured. In a real implementation, you would add your Credly and/or Accredible usernames to the config.toml file to display your actual badges.
{{< /notice >}}

