# PHP 8.3 Architecture Standards
- **Validation:** Always use `json_validate()` instead of `json_decode()` for checking JSON validity.
- **Constants:** Enforce Typed Class Constants (`public const string STATUS = 'active';`).
- **Overrides:** The `#[\Override]` attribute is mandatory for all overridden parent methods to ensure safe refactoring.