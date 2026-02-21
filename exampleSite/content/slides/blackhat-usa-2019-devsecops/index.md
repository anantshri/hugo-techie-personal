---
title: "DevSecOps: What, Why and How?"
date: 2019-08-07
draft: false

# Presentation metadata
conference: "Black Hat USA"
conference_url: "https://www.blackhat.com/us-19/"
event_year: 2019

# Location (for map)
location:
  city: "Las Vegas"
  state: "NV"
  country: "USA"
  latitude: 36.1699
  longitude: -115.1398

# Slides configuration
slides:
  pdf: "slides.pdf"
  page_count: 8
  download_enabled: true

# Video recordings
videos:
  - url: "https://www.youtube.com/watch?v=DzX9Vi_UQ8o"
    label: "Conference Recording"

# Resources / references
resources:
  - title: "Achieving DevSecOps with Open-Source Tools"
    url: "https://notsosecure.com/achieving-devsecops-open-source-tools"
  - title: "OWASP DevSecOps Guideline"
    url: "https://owasp.org/www-project-devsecops-guideline/"

# Social media buzz
social_chatter:
  - url: "https://twitter.com/InfosecVandana/status/1159529386397200384"
    platform: twitter
  - url: "https://twitter.com/notsosecure/status/1159525342001807361"
    platform: twitter

# Cross-references
timeline_entry: "/timeline/blackhat-usa-2019/"
related_presentations:
  - "/slides/nullcon-2018-mobile-security/"

# Taxonomies
tags: [devsecops, ci-cd, supply-chain, security-tools]
focus: [application-security, devsecops]
activity: talk

# OEmbed metadata
oembed:
  author_name: "Anant Shrivastava"
  author_url: "https://anantshri.info"
  provider_name: "Anant Shrivastava"
  provider_url: "https://anantshri.info"
---

Security is often added towards the end, in a typical DevOps cycle. This talk covers how to integrate security into each phase of DevOps — from code commit to deployment — using freely available open-source tools.

We walk through a practical pipeline that includes SAST, DAST, dependency scanning, container security, and infrastructure-as-code auditing, all orchestrated via CI/CD. The goal: make security a first-class citizen in every sprint, not an afterthought bolted on at release time.
