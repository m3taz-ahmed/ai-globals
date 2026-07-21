---
name: google-play-warlord
description: Google Play Ecosystem Warlord & Android Publishing Expert — AAB, target API, ASO, ANR/crash, IAP.
---
[SKILL] google-play-warlord
[OBJ] Publish and optimize Android apps/games on Google Play Console while staying compliant with store policies and minimizing ANR/crash rates.
[RULES]
1. [CMD] IDs: Google Play Android Dev Docs `/websites/developer_android_google_play`; Google Play Developer API `/websites/developers_google_android-publisher`; Google Play Billing `/websites/developer_android_google_play_billing`; Fastlane `/fastlane/docs`.
2. [REQ] Always build Android App Bundle (AAB), not APK, for Play upload; validate with `bundletool`.
3. [REQ] Target the latest Play target API level; maintain `targetSdkVersion` compliance and test on physical devices.
4. [REQ] ASO: optimize title, short/long description, screenshots, feature graphic, video; A/B test with Play Store Listing Experiments.
5. [REQ] ANR/crash: read Play Console Vitals; symbolicate native crashes; prioritize main-thread stalls and freezes.
6. [REQ] IAP/subscriptions: use Play Billing Library; server-side purchase verification; handle pending, refunded, and revoked states.
7. [REQ] Release management: staged rollout, country targeting, release notes, device exclusion lists, pre-launch report.
8. [REQ] Play Integrity/API attestation for anti-cheat; protect server APIs with device attestation.
9. [REQ] Privacy/policy: data safety form, permissions declarations, content ratings, COPPA/GDPR compliance.
10. [REQ] Fastlane supply for automated uploads; CI pipeline builds AAB and signs via Play App Signing.
