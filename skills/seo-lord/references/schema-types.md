# Schema.org Structured Data Types
[REF] schema-types
[OBJ] Schema.org structured data types — Active, Deprecated, Keep — with JSON-LD rules.

## Active Types (recommend for rich results)
- Organization: logo, contactPoint, sameAs (social profiles).
- WebSite: SearchAction (sitelinks searchbox).
- Article: headline, datePublished, dateModified, author, image, publisher.
- Product: name, image, offers (price, currency, availability), sku, gtin, aggregateRating, shippingDetails, hasMerchantReturnPolicy.
- BreadcrumbList: itemListElement (position, name, item).
- LocalBusiness: subtypes (Restaurant, LegalService, AutoDealer, MedicalClinic), address, geo, openingHoursSpecification, telephone.
- Event: name, startDate, location, offers.
- Person: name, jobTitle, worksFor, sameAs.
- JobPosting: title, datePosted, hiringOrganization, jobLocation.
- Course: name, provider, description.
- Review: itemReviewed, reviewRating, author.
- AggregateRating: itemReviewed, ratingValue, reviewCount.
- VideoObject: name, uploadDate, thumbnailUrl, contentUrl.
- ImageObject: caption, contentUrl.
- DiscussionForumPosting: For forum content.

## E-commerce Specific
- ProductGroup: variant products.
- Offer: price, priceCurrency, availability, itemCondition.
- hasMerchantReturnPolicy: required for Merchant Center.
- shippingDetails: required for Merchant Center.
- hasAdultConsideration: required for adult products.

## Deprecated (NEVER recommend for rich results)
- HowTo: Deprecated Sept 2023. No rich results.
- SpecialAnnouncement: Deprecated July 2025.
- CourseInfo/EstimatedSalary/LearningVideo/ClaimReview/VehicleListing: Deprecated June 2025.
- Practice Problem: Deprecated 2026-01-06.

## No Rich Results (keep if useful for structure)
- FAQPage: Retired May 7, 2026. Use QAPage for genuine Q&A only.
- ⛔ Do NOT recommend FAQPage for Google SERP benefit.

## JSON-LD Rules
- JSON-LD preferred (Google's stated preference). Microdata/RDFa accepted but JSON-LD is standard.
- Dual validation: Rich Results Test (search.google.com/test/rich-results) + Schema Markup Validator (validator.schema.org).
- Schema drift detection: Compare JSON-LD properties against visible page content. Flag mismatches.
- Required vs recommended properties per type (check schema.org docs).
- Nested types where appropriate (e.g., Product inside Offer inside ItemList).

## Schema Drift Detection
- Extract JSON-LD from page.
- Extract visible text content.
- Compare: Does schema match what user sees?
- Flag: Schema claims "price: 29.99" but page shows "$39.99" = drift.
- Flag: Schema claims "inStock" but page shows "Out of stock" = drift.
- Critical for e-commerce (Merchant Center suspensions for mismatch).
