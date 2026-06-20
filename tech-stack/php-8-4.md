[TECH] php-8-4
[OBJ] PHP 8.4 Bleeding Edge Standards.
[RULES]
1. [REQ] Syntax: Property Hooks (get/set). Asymmetric Visibility (`public private(set)`). Chain on instantiation `(new Service())->execute()`.
2. [REQ] APIs: `DOM\XMLDocument` > legacy `DOMDocument`. Array helpers (`array_find`, `array_any`, etc.). Object-style `bcadd`.
3. [REQ] Quality: `declare(strict_types=1);` in EVERY file.
