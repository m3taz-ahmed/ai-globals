# PHP 8.4 Bleeding Edge Standards

## 1. MODERN SYNTAX
- **Property Hooks:** Use property hooks (get/set) instead of boilerplate getter/setter methods for virtual or validated properties.
- **Asymmetric Visibility:** Prefer `public private(set)` for properties that should be readable globally but only modifiable within the class.
- **Instantiation:** Chain methods directly on instantiation: `(new Service())->execute()`.

## 2. NEW APIs & FEATURES
- **Modern DOM API:** Use the new `DOM\XMLDocument` and `DOM\HTMLDocument` for standard-compliant parsing. Avoid legacy `DOMDocument`.
- **Array Helpers:** Utilize `array_find`, `array_any`, `array_all`, and `array_find_key` for cleaner logic.
- **BCMath Improvements:** Use the new `bcadd`, `bcsub` with object-style operator overloading where applicable.

## 3. QUALITY GATES
- **Strict Typing:** Every file MUST have `declare(strict_types=1);`.
- **Deprecated Features:** Never use `#[\Deprecated]` features from 8.3 in 8.4 code.