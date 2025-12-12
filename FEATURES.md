# ImageArchive - Feature Guide

## Tagging System

### Adding Multiple Tags at Once

**New feature:** Add multiple tags in one go using space-separated format!

**Basic usage:**
```
landscape sunset beach
```
This adds 3 tags: `landscape`, `sunset`, `beach`

**Multi-word tags with quotes:**
```
landscape "golden hour" beach
```
This adds 3 tags: `landscape`, `golden hour`, `beach`

**Mixed format:**
```
portrait "street photography" black-and-white candid
```
Adds: `portrait`, `street photography`, `black-and-white`, `candid`

**How to use:**
1. Open an image
2. Type tags in the input field: `tag1 "tag 2" tag3`
3. Press Enter (or click Add)
4. All tags are added at once!

**Features:**
- Space-separated tags
- Quotes for multi-word tags
- Press Enter to submit
- Automatic duplicate detection
- Shows count: "3 tags added successfully"

## Advanced Search

### Search Syntax

**Simple search** (searches everything):
```
nikon
```
Finds: images with "nikon" in any field (tags, camera, description, etc.)

**Tag-specific search:**
```
tag:landscape
```
Finds: images that have the tag "landscape"

**Date-specific search:**
```
date:2024
date:2024-12
date:2024-12-25
```
Finds: images from 2024, December 2024, or Christmas Day 2024

**Combined search:**
```
tag:landscape date:2024
```
Finds: images tagged "landscape" AND taken in 2024 (both conditions must match)

**Multi-word search:**
```
tag:"street photography" date:2024-12
```
Finds: images tagged "street photography" from December 2024

**Complex examples:**
```
tag:portrait nikon
→ Images tagged "portrait" that also mention "nikon" anywhere

tag:landscape date:2024 sunset
→ Images tagged "landscape" from 2024 with "sunset" in any field

tag:architecture date:2024-08 f/2.8
→ Architecture shots from August 2024 at f/2.8 aperture
```

### Search Behavior

**AND logic:**
- Multiple terms = ALL must match
- `tag:portrait date:2024` = portrait AND 2024

**OR logic:**
- Not supported directly
- Use separate searches

**Field search:**
- `tag:value` - searches only in tags
- `date:value` - searches only in date_taken
- No prefix - searches everywhere

## URL Sharing

### Share Specific Images

**Share button in modal:**
1. Open an image
2. Click "Share This Image" button
3. Link copied to clipboard automatically
4. Share the link!

**Manual sharing:**
- Just copy the URL from your browser when viewing an image
- URL format: `?image=rollfilm/batch/image_001`

**What happens when someone clicks your link:**
- Goes directly to your site
- Image opens in lightbox automatically
- They see the exact image you shared

### Share Searches

**Search for something → URL updates automatically:**
```
Search: tag:landscape date:2024
URL becomes: ?search=tag:landscape+date:2024
```

Share this URL and others see the same search results!

**Examples:**
```
?search=nikon
→ Shows all Nikon images

?search=tag:portrait+date:2024-12
→ Shows portraits from December 2024

?search=tag:architecture&type=sheetfilm
→ Shows architecture images from sheet film only
```

## Select Multiple (Floating Button)

### New Floating Button

The "Select Multiple" button now:
- ✅ Floats in bottom-right corner
- ✅ Always visible when scrolling
- ✅ Easy to access from anywhere on page
- ✅ Only shows when logged in

**Location:** Bottom-right corner with checkmark icon

**Usage:**
1. Click floating button (anywhere on page)
2. Click images to select
3. Use toolbar to tag selected images
4. Click button again to exit select mode

## EXIF Date Format

### Display Format

**Format:** YYYY-MM-DD HH:MM (24-hour time)

**Examples:**
```
2024-12-25 14:30
2025-01-15 09:15
2023-08-20 18:45
```

**Features:**
- ISO 8601 standard format
- 24-hour time (no AM/PM)
- No seconds (cleaner display)
- Sortable format

## Examples

### Example 1: Adding Multiple Tags

**Scenario:** Tagging a street photography image

```
Input: street candid "black and white" urban
Result: 4 tags added
- street
- candid
- black and white
- urban
```

### Example 2: Advanced Search

**Scenario:** Find all portraits from 2024 shot with Nikon

```
Search: tag:portrait date:2024 nikon
Results: Images that have ALL of:
  - Tag "portrait"
  - Taken in 2024
  - "nikon" appears anywhere (camera, description, etc.)
```

### Example 3: Sharing Workflow

**Scenario:** Share a favorite image with a friend

```
1. Search: tag:landscape date:2024-08
2. Open a beautiful sunset image
3. Click "Share This Image" button
4. Paste link in email/chat
5. Friend clicks link → sees same image
```

### Example 4: Date-based Search

**Scenario:** Find images from a specific trip

```
Search: date:2024-08 italy
Results: Images from August 2024 with "italy" in any field
```

Or just:
```
Search: 2024-08
Results: All images from August 2024
```

## Tips & Tricks

### Quick Tagging
- Type: `landscape sunset beach` + Enter
- Much faster than adding one-by-one!

### Search Refinement
- Start broad: `nikon`
- Add filters: `tag:portrait nikon`
- Add date: `tag:portrait nikon date:2024`

### URL Sharing
- Image URLs are permanent (as long as image_id doesn't change)
- Search URLs reflect exact search parameters
- Share with anyone - no login required to view

### Bulk Operations
- Use floating "Select Multiple" button (visible while scrolling)
- Select many images
- Add tags to all at once
- Fast workflow for organizing batches

