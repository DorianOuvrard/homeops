# Vision — hodoor-webapp

## Scope mode
SELECTIVE EXPANSION

## 11-star version
A home appliance concierge that lives in your pocket. You point your phone at any appliance, it identifies it instantly, builds your home inventory, and proactively schedules maintenance before things break. Voice-first, camera-native, zero friction. Every household object has a living profile with full maintenance history.

## Commitment
Build a mobile-first PWA (HODOOR) with authentication, conversational chat (text + photo), and appliance scan/history, reusing the existing bot backend as the API layer.

## Not building
Voice input/STT, real-time camera bounding-box detection (static photo upload for scan instead), push notifications for reminders (in-chat reminders only), native app store distribution, multi-household support, file management tab

## Why this scope
The mockups define a clear product vision with five screens, but real-time camera ML and voice are separate technical bets that would triple the timeline. Photo-based scan delivers 90% of the identification value. The existing bot backend already handles AI conversation, appliance identification, and maintenance logic, so the webapp is primarily a frontend + auth + persistence layer on top of proven capabilities.
