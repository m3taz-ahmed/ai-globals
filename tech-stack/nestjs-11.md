[TECH] NestJS 11
[OBJ] Progressive Node.js framework with modular architecture, dependency injection, and first-class TypeScript support.
[RULES]
1. [REQ] Organize the app into feature modules: each module encapsulates controllers, providers, and DTOs in its own directory (`src/features/<feature>/`).
2. [REQ] Use `@Module()` with explicit `imports`, `providers`, `controllers`, and `exports`; never use the `@Global()` decorator unless the provider is truly cross-cutting (logging, config).
3. [REQ] Use `@Injectable()` providers with constructor injection (`constructor(private readonly usersService: UsersService)`); never use property injection unless required by circular dependencies.
4. [REQ] Validate all input with `class-validator` decorators (`@IsString`, `@IsEmail`, `@MinLength`) on DTO classes and `ValidationPipe` globally: `app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }))`.
5. [REQ] Use guards (`@Injectable()` implementing `CanActivate`) for authorization; apply at controller or method level with `@UseGuards(JwtAuthGuard, RolesGuard)`.
6. [REQ] Use interceptors for cross-cutting concerns (logging, caching, transformation); keep controllers thin and delegate business logic to services.
7. [REQ] Use pipes for data transformation and validation; use filters (`@Catch()`) for centralized exception handling with consistent error response shape.
8. [REQ] Use `@nestjs/microservices` for event-driven communication (Redis, NATS, Kafka, RabbitMQ); define message patterns with `@MessagePattern()` and event patterns with `@EventPattern()`.
9. [REQ] Generate Swagger docs with `@nestjs/swagger`: annotate DTOs with `@ApiProperty()`, controllers with `@ApiTags()` and `@ApiOperation()`, and serve via `SwaggerModule.setup("docs", app, document)`.
10. [REQ] Use `@nestjs/config` with a validated schema (Joi or Zod) for environment variables; never access `process.env` directly in services.
11. [REQ] Use `@nestjs/typeorm` or `@nestjs/prisma` for database access; keep repository / Prisma service calls in service layer, never in controllers.
12. [REQ] Use `@nestjs/schedule` for cron jobs and intervals; register `ScheduleModule.forRoot()` in the root module.
13. [REQ] Use `helmet`, `compression`, and `class-transformer` (`plainToInstance`) for security and performance middleware.
14. [PROHIBIT] Never instantiate services manually with `new` — always use the DI container. Never use `any` in DTOs or service signatures.
15. [PROHIBIT] Never expose entity / ORM models directly in API responses — always map to a response DTO with `plainToInstance(ResponseDto, entity)`.
[COMPAT]
- v11.0: Node.js 20+, TypeScript 5.7+, Express 5 or Fastify 5 adapter, native Swagger module, improved DI.
[REFS]
- https://docs.nestjs.com/
- https://docs.nestjs.com/microservices/basics
- https://docs.nestjs.com/openapi/introduction
