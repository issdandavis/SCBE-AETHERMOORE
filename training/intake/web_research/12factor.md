# The Twelve-Factor App

The twelve-factor app is a methodology for building software-as-a-service applications that use declarative formats for setup automation, have a clean contract with the underlying operating system, are suitable for deployment on modern cloud platforms, minimize divergence between development and production, and can scale up without significant changes to tooling, architecture, or development practices.

## I. Codebase

One codebase tracked in revision control, many deploys. A twelve-factor app is always tracked in a version control system such as Git. A one-to-one correlation exists between the codebase and the app — if there are multiple codebases, it's a distributed system with each component being an app. Multiple apps sharing the same code is a violation — factor shared code into libraries. There is only one codebase per app, but there will be many deploys of the app (production, staging, developer local).

## II. Dependencies

Explicitly declare and isolate dependencies. A twelve-factor app never relies on implicit existence of system-wide packages. It declares all dependencies completely and exactly via a dependency declaration manifest. Uses a dependency isolation tool during execution to ensure no implicit dependencies leak in from the surrounding system. In Python: pip for declaration, virtualenv for isolation.

## III. Config

Store config in the environment. An app's config is everything that is likely to vary between deploys (staging, production, developer environments). This includes resource handles to databases, credentials to external services, per-deploy values such as canonical hostname. The twelve-factor app stores config in environment variables. Env vars are easy to change between deploys without changing code and are language/OS-agnostic.

## IV. Backing Services

Treat backing services as attached resources. A backing service is any service the app consumes over the network as part of its normal operation — datastores (MySQL, PostgreSQL), messaging/queueing systems (RabbitMQ, Beanstalkd), SMTP services, caching systems (Memcached, Redis). The code makes no distinction between local and third-party services. A deploy should be able to swap a local MySQL for Amazon RDS without code changes.

## V. Build, Release, Run

Strictly separate build and run stages. The build stage converts code repo into an executable bundle (fetching dependencies, compiling binaries). The release stage combines the build with the deploy's current config. The run stage launches a set of the app's processes against a selected release. Every release should have a unique release ID (timestamp or incrementing number). Releases are append-only and cannot be mutated once created.

## VI. Processes

Execute the app as one or more stateless processes. The app is executed in the execution environment as one or more processes. Twelve-factor processes are stateless and share-nothing. Any data that needs to persist must be stored in a stateful backing service, typically a database. The memory space or filesystem of the process can be used as a brief, single-transaction cache. Never assumes that anything cached in memory or on disk will be available on a future request.

## VII. Port Binding

Export services via port binding. The twelve-factor app is completely self-contained and does not rely on runtime injection of a webserver into the execution environment. The web app exports HTTP as a service by binding to a port and listening to requests coming in on that port. In development, the developer visits a service URL like http://localhost:5000/.

## VIII. Concurrency

Scale out via the process model. In the twelve-factor app, processes are a first class citizen. The process model truly shines when it comes time to scale out. The share-nothing, horizontally partitionable nature of twelve-factor app processes means that adding more concurrency is a simple and reliable operation. The array of process types and number of processes of each type is known as the process formation.

## IX. Disposability

Maximize robustness with fast startup and graceful shutdown. The twelve-factor app's processes are disposable, meaning they can be started or stopped at a moment's notice. Processes should strive to minimize startup time. Processes shut down gracefully when they receive a SIGTERM signal. For a web process, graceful shutdown is achieved by ceasing to listen on the service port, allowing current requests to finish, then exiting.

## X. Dev/Prod Parity

Keep development, staging, and production as similar as possible. The twelve-factor app is designed for continuous deployment by keeping the gap between development and production small. Make the time gap small (deploy hours after writing code). Make the personnel gap small (developers who wrote code are closely involved in deploying it). Make the tools gap small (keep development and production as similar as possible).

## XI. Logs

Treat logs as event streams. A twelve-factor app never concerns itself with routing or storage of its output stream. It should not attempt to write to or manage logfiles. Instead, each running process writes its event stream, unbuffered, to stdout. In staging or production deploys, each process stream will be captured by the execution environment and collated with all other streams from the app for viewing and long-term archival.

## XII. Admin Processes

Run admin/management tasks as one-off processes. One-off admin processes should be run in an identical environment as the regular long-running processes of the app. They run against a release, using the same codebase and config as any process run against that release. Admin code must ship with application code to avoid synchronization issues.
