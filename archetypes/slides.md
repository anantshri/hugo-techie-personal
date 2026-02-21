---
title: "{{ replace .Name "-" " " | title }}"
date: {{ .Date }}
draft: true

# Presentation metadata
conference: ""
conference_url: ""
event_year: {{ now.Format "2006" }}

# Location (for map)
location:
  city: ""
  country: ""
  latitude: 0
  longitude: 0

# Slides configuration
slides:
  pdf: "slides.pdf"
  page_count: 0
  external_url: ""
  download_enabled: true

# Video recordings
videos: []

# Whitepaper (optional)
whitepaper:
  pdf: ""
  title: ""
  abstract: ""
  co_authors: []

# Resources / references
resources: []

# Social media buzz
social_chatter: []

# Cross-references
timeline_entry: ""
hacking_archives: ""
related_presentations: []

# Taxonomies
tags: []
focus: []
activity: talk

# OEmbed metadata
oembed:
  author_name: ""
  author_url: ""
  provider_name: ""
  provider_url: ""
---

<!-- Abstract / description -->
