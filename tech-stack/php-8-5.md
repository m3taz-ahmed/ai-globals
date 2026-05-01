# PHP 8.5 Architecture Standards
- **Pattern Matching & Enums:** Maximize the use of advanced pattern matching with Enums for state machines.
- **JIT Optimization:** Write code optimized for the improved Just-In-Time compiler. Avoid dynamic properties completely.
- **Typing:** Strict typing (`declare(strict_types=1);`) is absolute. Use Intersection and Union types natively without PHPDoc fallbacks.