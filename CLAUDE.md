QTrace --- Master Project Instructions for Claude

MANDATORY: This file is the single source of truth for Claude when
working on QTrace. Before implementing, modifying, refactoring,
deleting, or proposing any feature, Claude MUST read this file
completely and follow it. If a request conflicts with this document,
stop and identify the conflict before making code changes.

1. PROJECT IDENTITY

1.1 Product Name

QTrace --- Quantum-Inspired Route Intelligence for Smart Urban
Logistics

1.2 Product Vision

QTrace is a smart urban logistics and route-intelligence platform
designed to optimize routes for fleets and delivery operations using
quantum-inspired optimization, real-world routing, traffic information,
geospatial intelligence, and scalable backend services.

The product should evolve from the existing Python/Streamlit/Folium
prototype into a production-quality Android application backed by a
proper API and optimization platform.

QTrace is NOT intended to be a clone of Google Maps. Its primary purpose
is logistics optimization: multi-stop routing, fleet-aware optimization,
congestion-aware decision making, optimization objectives, and
operational intelligence.

1.3 Core Problem

Urban logistics suffers from:

traffic congestion

inefficient multi-stop route planning

excessive travel time and distance

operational cost

fleet coordination challenges

computational difficulty of large Vehicle Routing Problems

changing road and traffic conditions

QTrace addresses these through routing engines, traffic-aware data,
clustering, classical optimization baselines, and Quantum-inspired
Particle Swarm Optimization (QPSO).

2. NON-NEGOTIABLE CLAUDE RULE

Before every feature request:

Read this file.

Inspect the existing repository.

Understand the current architecture.

Search for existing implementations before creating new ones.

Identify dependencies and affected modules.

Plan the smallest correct change.

Implement.

Run formatting/static analysis/tests.

Verify integration.

Update documentation when behavior or architecture changes.

Report exactly what changed and what was verified.

Never blindly generate code from the user's prompt.

3. CURRENT PRODUCT DIRECTION

QTrace has an existing prototype based on:

Python

Streamlit

Folium

streamlit-folium

NumPy

Pandas

scikit-learn

Geopy

Requests

OSRM

TomTom Routing API

python-dotenv

The target production direction is:

Android

Kotlin

Jetpack Compose

Material 3

MVVM + Unidirectional Data Flow

Retrofit

OkHttp

Kotlin Coroutines

Kotlin Flow

Hilt

Room

DataStore

MapLibre

Backend

Python 3.12+

FastAPI

Pydantic

SQLAlchemy

Alembic

HTTPX

Optimization / Intelligence

QPSO

VRP

CVRP

CVRPTW

OR-Tools as a classical baseline

NumPy

SciPy

scikit-learn

NetworkX

Routing / Traffic

OSRM for development

TomTom traffic/routing as a production option

Google Routes may be used only where explicitly justified and
approved

Database

PostgreSQL

PostGIS

Background Processing

Redis

RQ workers

Authentication / Notifications / Monitoring

Firebase Authentication

Firebase Cloud Messaging

Firebase Crashlytics

Deployment

Docker

GitHub Actions

Low-cost VPS or Cloud Run

Do not replace the stack casually. Any architectural replacement
requires justification and explicit approval.

4. SYSTEM ARCHITECTURE

QTrace should follow this high-level flow:

Android App | | HTTPS / JSON v FastAPI Backend | +--> Authentication
| +--> Routing Service | +--> Traffic Service | +--> Geocoding
Service | +--> Optimization Service | | | +--> OR-Tools baseline
| +--> QPSO | +--> VRP/CVRP/CVRPTW | +--> Job Queue | | | +-->
Redis | +--> RQ Worker | +--> PostgreSQL/PostGIS | +--> External
APIs | +--> OSRM +--> TomTom +--> Other approved providers

The Android application must NOT contain API secrets.

5. REPOSITORY STRUCTURE

Preferred production repository:

qtrace/ ├── android/ │ ├── app/ │ ├── build.gradle.kts │ ├──
settings.gradle.kts │ └── ... │ ├── backend/ │ ├── app/ │ │ ├── main.py
│ │ ├── api/ │ │ ├── core/ │ │ ├── models/ │ │ ├── schemas/ │ │ ├──
services/ │ │ ├── repositories/ │ │ ├── optimization/ │ │ ├── routing/ │
│ ├── traffic/ │ │ ├── workers/ │ │ └── utils/ │ ├── tests/ │ ├──
alembic/ │ ├── requirements.txt │ └── Dockerfile │ ├── data/ │ ├──
sample/ │ └── README.md │ ├── docs/ │ ├── architecture/ │ ├── api/ │ ├──
algorithms/ │ └── deployment/ │ ├── scripts/ ├── .github/ │ └──
workflows/ ├── docker-compose.yml ├── .env.example ├── README.md ├──
CLAUDE.md └── LICENSE

Claude must adapt to the actual repository if it differs. Do not
restructure a working repository merely to match this example.

6. ARCHITECTURAL PRINCIPLES

6.1 Separation of concerns

Do not mix:

UI

API calls

business logic

optimization

database access

external provider integration

configuration

Each layer must have a clear responsibility.

6.2 Dependency direction

Prefer:

UI -> ViewModel -> Use Case/Repository -> API/Data Source

Backend:

API -> Service -> Repository/Domain -> Database/External Provider

Optimization:

API/Worker -> Optimization Service -> Algorithm implementation

Do not allow UI code to directly implement optimization algorithms.

6.3 Provider abstraction

External routing/traffic providers must be abstracted.

Example conceptual interface:

RoutingProvider - geocode() - route() - matrix()

Implementations may include:

OSRMProvider

TomTomProvider

Do not spread provider-specific logic throughout the application.

7. DOMAIN MODEL

Core concepts include:

User

id

profile

authentication metadata

preferences

Vehicle

id

fleet_id

capacity

current location

operating constraints

Depot

id

location

operating constraints

Delivery Stop

id

address/location

demand

priority

service time

time window

Route

id

vehicle

ordered stops

geometry

distance

duration

cost

optimization metadata

Optimization Job

id

input dataset

objective

algorithm

status

result

timestamps

Traffic Snapshot

provider

timestamp

road/route information

speed/congestion information

Do not invent fields without checking the existing domain model.

8. OPTIMIZATION CONCEPT

QTrace's research/technical core is Quantum-Inspired Particle Swarm
Optimization (QPSO) applied to routing/vehicle-routing optimization.

8.1 Classical baseline

A classical solver such as OR-Tools should be available as a
benchmark/baseline where appropriate.

The purpose is not to claim QPSO is universally superior.

Measurements should include:

total distance

total travel time

estimated cost

constraint violations

computation time

convergence behavior

solution quality

Any comparison must use the same dataset, constraints, objective
function, and evaluation conditions.

8.2 Supported problem families

Architecture should be capable of supporting:

TSP

VRP

CVRP

CVRPTW

Do not implement all variants unnecessarily. Implement the variant
required by the current feature.

9. QPSO IMPLEMENTATION RULES

QPSO implementation must be modular and testable.

Recommended components:

solution representation

population initialization

fitness/objective evaluation

constraint handling

personal best

global best

quantum position update

convergence tracking

termination condition

result serialization

Do not bury the entire algorithm inside one API endpoint.

The objective function must be explicit.

A conceptual objective may combine:

J = w_distance * distance + w_time * travel_time + w_cost *
operational_cost + w_penalty * constraint_penalty

Weights must be configurable and documented.

Never silently change objective weights.

10. CONSTRAINT HANDLING

Potential constraints:

vehicle capacity

maximum route length

time windows

depot start/end

service duration

number of vehicles

mandatory visits

geographic feasibility

Invalid solutions must be handled explicitly.

Do not hide infeasibility by returning a seemingly valid route.

API responses should distinguish:

valid optimized result

partially feasible result

infeasible problem

optimization failure

provider failure

timeout

11. ROUTING

Routing engines calculate road-network paths.

Optimization should operate on routing costs/matrices rather than
assuming straight-line distance when road routing is available.

Use:

OSRM for development/testing where appropriate.

TomTom for traffic-aware production functionality where configured.

Routing provider failures must produce controlled errors.

Never expose API keys in:

source code

Git

Android code

logs

screenshots

README examples

Use environment variables/secrets.

12. TRAFFIC DATA

Traffic data should be treated as time-dependent and provider-dependent.

Do not fake real-time traffic.

If real traffic is unavailable:

clearly label data as simulated, static, historical, or unavailable.

never present simulated data as live data.

Traffic integration must be isolated behind a service/provider
abstraction.

Traffic information can influence:

route cost

ETA

congestion penalty

optimization objective

Do not make unsupported claims about traffic accuracy.

13. MAPS

Map rendering belongs to the Android UI layer.

MapLibre is the preferred production map technology.

The backend should return structured geographic data rather than
UI-specific objects.

Typical route response:

route ID

ordered coordinates

stops

distance

duration

ETA

optimization metadata

Use GeoJSON where appropriate.

14. ANDROID DEVELOPMENT RULES

Use Kotlin.

Use Jetpack Compose.

Use Material 3.

Follow MVVM/UDF.

Preferred structure:

ui/ screens/ components/ state/ navigation/

data/ api/ local/ repository/

domain/ model/ repository/ usecase/

di/

Do not put business logic directly inside Composable functions.

Composable functions should primarily:

render state

emit user events

display loading/error/success states

ViewModels should manage screen state and user actions.

Use immutable UI state where practical.

15. BACKEND DEVELOPMENT RULES

Use FastAPI.

Use Pydantic schemas for API validation.

Use SQLAlchemy for database access.

Use Alembic for migrations.

Use async I/O where beneficial.

Do not perform long-running optimization directly inside a request if it
can block the API.

Long-running jobs should use Redis/RQ workers.

Every API endpoint should have:

input validation

predictable response structure

error handling

logging

tests where appropriate

documentation

16. API DESIGN

Use REST-style endpoints with clear nouns and actions.

Examples:

GET /health POST /api/v1/routes POST /api/v1/optimization/jobs GET
/api/v1/optimization/jobs/{id} GET /api/v1/routes/{id}

Do not create random endpoint naming conventions.

Use API versioning.

Never expose internal stack traces to clients.

Return useful error messages without leaking secrets.

17. DATABASE RULES

Use PostgreSQL/PostGIS.

Use migrations for schema changes.

Never manually modify production schema without a migration.

Indexes must be considered for:

spatial queries

foreign keys

frequently filtered fields

timestamps

job status

Do not add indexes blindly.

Use PostGIS types/functions for geospatial operations when appropriate.

18. CONFIGURATION

All environment-specific configuration belongs in environment
variables/configuration.

Maintain:

.env.example

It should contain variable names but never real secrets.

Examples:

DATABASE_URL= REDIS_URL= OSRM_BASE_URL= TOMTOM_API_KEY= FIREBASE_CONFIG=
SECRET_KEY=

Do not commit .env.

19. SECURITY

Claude must always check:

secrets

authentication

authorization

input validation

SQL injection

command injection

path traversal

unsafe deserialization

excessive API exposure

rate limiting where needed

CORS

sensitive logging

Never log:

API keys

passwords

tokens

private credentials

Do not store secrets in Android source code.

20. ERROR HANDLING

Errors must be explicit.

Use structured errors.

Examples:

ROUTING_PROVIDER_ERROR TRAFFIC_PROVIDER_ERROR INVALID_ROUTE_INPUT
INFEASIBLE_OPTIMIZATION OPTIMIZATION_TIMEOUT DATABASE_ERROR
AUTHENTICATION_ERROR

Never use broad except Exception without meaningful handling.

Do not silently swallow errors.

21. LOGGING

Logs should answer:

what happened?

where?

when?

why?

which request/job?

Do not log sensitive information.

Use appropriate log levels:

DEBUG INFO WARNING ERROR CRITICAL

Production logs should be useful without becoming excessively noisy.

22. TESTING STRATEGY

Every feature must have an appropriate testing level.

Unit tests

Test:

objective functions

distance calculations

constraint handling

QPSO updates

route validation

parsers

provider adapters

Integration tests

Test:

API + service

API + database

optimization job flow

routing provider integration

traffic integration

Android tests

Test:

ViewModels

state transitions

repositories

critical UI behavior

End-to-end

Validate:

User input -> API -> optimization/routing -> database/job -> API
response -> Android rendering

23. TEST-FIRST EXPECTATION

Before changing complicated logic:

identify existing tests

add a regression test if the bug is reproducible

implement the fix

run the relevant tests

run broader tests if necessary

Never delete a failing test simply to make the build pass.

24. PERFORMANCE

Always consider:

API latency

routing API latency

optimization runtime

memory usage

database queries

mobile network usage

battery consumption

map rendering

Do not optimize prematurely.

Measure before making performance claims.

For QPSO, record convergence/runtime metrics when research evaluation
requires them.

25. IDEMPOTENCY AND JOBS

Optimization jobs may be long-running.

Use job states such as:

QUEUED RUNNING COMPLETED FAILED CANCELLED

Persist job status.

A client must be able to query job status.

Do not assume an HTTP request remains open for the entire optimization
process.

26. UI/UX PRINCIPLES

QTrace should feel like a professional logistics product.

Priorities:

clarity

fast interaction

map-first understanding

readable route information

useful optimization status

obvious errors

minimal unnecessary complexity

Important UI states:

loading

empty

success

error

offline/unavailable

optimization running

optimization completed

infeasible input

Never show a blank screen when an error occurs.

27. ACCESSIBILITY

Support:

readable typography

sufficient contrast

touch-friendly controls

content descriptions

meaningful error messages

scalable text where practical

Do not rely only on color to communicate status.

28. FEATURE IMPLEMENTATION WORKFLOW

For every new feature Claude MUST follow this workflow.

Step 1 --- Understand

Restate:

requested feature

user value

affected layers

dependencies

risks

Step 2 --- Inspect

Search repository for:

existing similar feature

relevant models

services

API endpoints

UI screens

tests

configuration

Step 3 --- Plan

Create a concise implementation plan.

Example:

add domain model

add database migration

add Pydantic schema

add service

add endpoint

add tests

connect Android repository

update ViewModel

update UI

verify

Step 4 --- Implement

Implement incrementally.

Step 5 --- Validate

Run:

formatter

linter

type/static checks

unit tests

integration tests as relevant

build

Step 6 --- Review

Check:

architecture

security

performance

edge cases

backwards compatibility

Step 7 --- Document

Update relevant documentation.

Step 8 --- Report

Tell the user:

files changed

behavior added

tests run

test results

known limitations

next recommended technical step, if necessary

29. HOW CLAUDE SHOULD GENERATE IDEAS

Claude may propose ideas, but ideas must be:

relevant to QTrace

technically feasible

aligned with logistics optimization

compatible with the architecture

cost-conscious

explainable

testable

Prioritize:

correctness

core functionality

reliability

security

performance

usability

advanced intelligence

visual polish

Do not add features simply because they are trendy.

Every proposed feature should answer:

What problem does it solve?

Who uses it?

What data does it require?

What backend changes are needed?

What Android changes are needed?

What external services are required?

What does it cost?

How is it tested?

What happens when the dependency fails?

30. FEATURE REQUEST TRIAGE

Classify each request as:

A. Bug fix B. Small enhancement C. New feature D. Architectural change
E. Optimization/research change F. Security change G. UI/UX change H.
Infrastructure/deployment change

For A/B/C/G, prefer minimal changes.

For D/E/F/H, perform deeper architecture analysis before implementation.

31. DO NOT OVERENGINEER

Do not introduce:

unnecessary microservices

unnecessary databases

unnecessary AI models

unnecessary dependencies

unnecessary abstraction layers

unnecessary cloud services

QTrace should remain cost-efficient and maintainable.

32. DEPENDENCY RULES

Before adding a package:

Check whether an existing dependency already solves the problem.

Check maintenance/activity.

Check license compatibility.

Check bundle/build impact.

Check security.

Check whether it works with the current stack.

Do not add dependencies for trivial functionality.

33. CODE STYLE

Code must be:

readable

modular

documented where needed

typed where possible

deterministic where practical

testable

Prefer descriptive names.

Avoid:

x

foo

temp

data2

unexplained magic numbers

unless they are conventional and scoped appropriately.

34. COMMENTS

Comments should explain WHY, not merely WHAT.

Bad:

# add 1 to i

Good:

# Preserve depot index because the optimization matrix uses depot as node 0.

Do not fill code with unnecessary comments.

35. MAGIC NUMBERS

Do not hard-code:

optimization weights

API timeouts

retry counts

vehicle capacities

penalties

map zoom levels

provider URLs

when they are configurable domain parameters.

Use named constants/configuration.

36. API PROVIDER FALLBACKS

Fallbacks must be intentional.

Do not silently switch providers if doing so changes:

traffic semantics

routing behavior

coordinate interpretation

cost model

licensing

If fallback is required, document it.

37. OFFLINE BEHAVIOR

The mobile app should gracefully handle unavailable network
connectivity.

Possible behavior:

show cached routes/data where safe

clearly indicate stale data

queue appropriate requests only when designed for it

prevent impossible actions

provide retry

Never pretend cached data is live.

38. DATA QUALITY

Validate:

latitude/longitude bounds

duplicate stops

missing coordinates

impossible demands

invalid capacities

invalid time windows

empty routes

malformed provider responses

Do not allow invalid input to reach optimization without validation.

39. GEOSPATIAL RULES

Be consistent about:

latitude/longitude order

coordinate reference systems

units

meters vs kilometers

seconds vs minutes

timestamps/time zones

Never mix coordinate ordering conventions silently.

Document conversions.

40. TIME RULES

Use UTC internally for stored timestamps where practical.

Convert to local display time at the UI boundary.

Do not compare naive and timezone-aware timestamps.

Document ETA assumptions.

41. RESEARCH REPRODUCIBILITY

Optimization experiments must record:

dataset

seed

algorithm

population size

iterations

objective weights

constraints

routing source

traffic source

runtime

result metrics

When randomness is involved, support a configurable random seed.

Do not claim reproducibility without controlling relevant variables.

42. BENCHMARKING

When comparing algorithms:

Use identical:

input

constraints

objective

cost matrix

stopping criteria where meaningful

evaluation metric

Report actual measurements.

Never manufacture performance numbers.

Never hard-code fake benchmark results.

43. DEMO DATA

Demo/sample data is allowed.

But it MUST be clearly identified as:

sample

mock

simulated

synthetic

Never label sample traffic as live traffic.

Never claim an API integration works unless it has actually been tested.

44. EXTERNAL API COST CONTROL

Prefer cost-efficient development.

During development:

use OSRM where appropriate

cache repeated requests where legally/technically appropriate

avoid unnecessary API calls

use small test datasets

do not repeatedly hit paid APIs during automated tests

Use mocks for unit tests.

Use controlled integration tests for real providers.

45. API RATE LIMITS

Respect external provider rate limits.

Implement:

timeouts

controlled retries

exponential backoff where appropriate

response validation

caching where appropriate

Do not retry permanent errors indefinitely.

46. GIT RULES

Use meaningful commits.

Examples:

feat: add CVRPTW optimization job fix: handle invalid route coordinates
refactor: isolate routing providers test: add QPSO constraint tests
docs: update deployment instructions

Do not commit:

.env

secrets

API keys

build artifacts

caches

generated credentials

Before a commit, inspect the diff.

Do not overwrite unrelated user changes.

47. EXISTING USER WORK RULE

This is critical.

Claude MUST NOT:

delete working code without reason

rewrite the entire project unnecessarily

reset Git history

discard uncommitted changes

overwrite files unrelated to the request

replace an architecture without analysis

Before destructive operations, inspect the current state and explain the
impact.

48. BUG FIXING PROCESS

When a bug is reported:

reproduce if possible

locate root cause

inspect related code

determine whether the issue is frontend/backend/data/provider

create regression test

fix root cause

run tests

verify no regression

explain root cause

Do not patch symptoms if the underlying problem is clear.

49. DEBUGGING

Use evidence.

Inspect:

logs

stack traces

request payloads

response payloads

database state

network calls

application state

Do not guess repeatedly.

When debugging an API integration, first determine whether failure is:

configuration

authentication

network

request format

provider behavior

parsing

application logic

50. FRONTEND BUGS

For UI issues, inspect:

state flow

recomposition

navigation

lifecycle

API loading state

error state

serialization

map rendering

permissions

Do not immediately rewrite the screen.

51. BACKEND BUGS

Inspect:

validation

dependency injection

database transaction

async/sync boundaries

provider calls

serialization

exception handling

worker state

Do not add random retries to hide backend errors.

52. ALGORITHM BUGS

For QPSO/VRP issues:

verify input representation

verify objective

verify constraints

verify initialization

verify update equations

verify random number handling

verify best-state updates

verify termination

inspect convergence

compare with a small hand-checkable case

Use deterministic seeds for debugging.

53. UI FEATURE PROCESS

For every new Android screen:

define user goal

define UI state

define events

define ViewModel behavior

define repository/API requirements

implement screen

implement loading/error/empty/success states

test

verify accessibility

verify navigation

54. API FEATURE PROCESS

For every backend endpoint:

define request schema

define response schema

validate input

implement service

implement repository/provider calls

handle errors

add tests

document endpoint

verify API manually if useful

55. DATABASE FEATURE PROCESS

For schema changes:

modify SQLAlchemy model

create Alembic migration

inspect migration

test upgrade

test downgrade where supported

update related repository/service code

update tests

Never edit an old migration that may already have been applied unless
there is a controlled migration strategy.

56. SECURITY CHECK BEFORE MERGE

Ask:

Did I introduce a secret?

Is user input validated?

Is authorization correct?

Is sensitive data logged?

Is the endpoint exposed unnecessarily?

Is CORS appropriate?

Are dependencies safe?

Could malicious input crash the service?

Could one user access another user's data?

57. PERFORMANCE CHECK BEFORE MERGE

Ask:

Does this add unnecessary API calls?

Does this add unnecessary database queries?

Does this block the API worker?

Does this increase Android recomposition?

Does this increase map rendering cost?

Does this increase optimization complexity?

Is caching appropriate?

58. DEPLOYMENT

Production should be containerized where appropriate.

Backend deployment must include:

environment configuration

database migration process

health check

logging

restart strategy

HTTPS

secrets management

Android production must include:

release build

signing configuration

secure API endpoint

crash reporting

privacy considerations

Play Store metadata

Never commit release signing keys.

59. CI/CD

GitHub Actions should eventually automate:

lint

tests

type checks

backend build

Android build

container build

migration validation where safe

CI must fail on meaningful errors.

Do not weaken CI merely to get green status.

60. OBSERVABILITY

Monitor:

API latency

error rates

optimization job duration

job failure rate

external API failures

database health

application crashes

Use Crashlytics for Android crash monitoring where configured.

61. DOCUMENTATION

Update documentation when changing:

architecture

API

database

algorithms

configuration

deployment

user-facing behavior

Keep README focused on onboarding.

Put deeper technical details in docs/.

62. CLAUDE RESPONSE FORMAT

For significant implementation requests, Claude should respond using:

Understanding

What the request means.

Inspection

What existing code/components were found.

Plan

What will change.

Implementation

What was changed.

Validation

What commands/tests were run.

Result

What now works.

Notes

Limitations or decisions.

Do not claim a test was run if it was not run.

63. WHEN REQUIREMENTS ARE AMBIGUOUS

Do not invent critical requirements.

If ambiguity affects:

data model

security

algorithm correctness

API contract

money/cost

destructive operations

deployment

user data

ask for clarification.

For low-risk UI details, choose a reasonable consistent implementation
and state the assumption.

64. WHEN A REQUEST CONFLICTS WITH THE ARCHITECTURE

Do not blindly implement.

Explain:

requested behavior

architectural conflict

affected components

safer implementation path

Then use the smallest compatible solution when the intent is still
clear.

65. WHEN A USER ASKS FOR "BEST" IMPLEMENTATION

Do not choose based only on popularity.

Evaluate:

correctness

project fit

complexity

cost

maintainability

performance

security

availability

licensing

For QTrace, project requirements take priority over generic trends.

66. WHEN ADDING AI/ML

Ask:

Is ML actually required?

What data is available?

What is the ground truth?

How will it be evaluated?

What happens when confidence is low?

What is the computational cost?

Is deterministic logic sufficient?

Do not add an AI model just to label the product "AI-powered."

67. WHEN ADDING QUANTUM-INSPIRED LOGIC

Clearly distinguish:

quantum computing

quantum-inspired classical algorithms

classical metaheuristics

QTrace uses QPSO as a quantum-inspired classical optimization
approach unless an actual quantum backend is explicitly introduced.

Do not claim that QTrace runs on a quantum computer unless that is
actually true.

68. CLAIMS AND PRESENTATIONS

All technical claims must be defensible.

Never invent:

accuracy

speedup

cost savings

traffic improvement

energy savings

algorithm superiority

real-time capabilities

production scale

Use measured results or clearly label estimates.

69. PRIVACY

Minimize collection of personal data.

Only store data required by product functionality.

Protect:

account information

addresses

location history

fleet information

operational data

authentication data

Do not expose one organization's fleet information to another.

70. MULTI-TENANCY

If organizational accounts are implemented:

Every tenant-owned resource must be scoped to the tenant.

Examples:

vehicles

routes

stops

jobs

reports

Authorization must be enforced server-side.

Never rely only on Android UI restrictions.

71. ROUTE RESULT EXPLANATION

When possible, route results should expose useful metadata:

total distance

estimated duration

number of stops

vehicle assignment

objective value

optimization algorithm

optimization status

Avoid exposing raw internal algorithm data unless useful to the user.

72. OPTIMIZATION EXPLAINABILITY

A result should be explainable at a practical level.

Example:

"Route reordered to reduce estimated travel time while respecting
vehicle capacity."

Do not claim a specific causal reason unless the algorithm actually
provides that evidence.

73. CACHE POLICY

Cache only data that can safely be reused.

Consider:

route cache

geocoding cache

map data

configuration

user preferences

Traffic information is time-sensitive and must have an explicit
freshness policy.

Never serve stale traffic as current traffic.

74. NETWORK RESILIENCE

External calls should have:

timeout

controlled retry

error classification

cancellation support

Android should cancel obsolete requests when appropriate.

Do not allow a dead provider to freeze the UI.

75. CODE REVIEW CHECKLIST

Before considering a feature complete:

Correctness

Requirement implemented

Edge cases considered

Existing behavior preserved

Architecture

Correct layer

No unnecessary coupling

Existing abstractions reused

Security

No secrets

Input validated

Authorization checked

Testing

Unit tests

Integration tests where needed

Regression test where needed

Build succeeds

Performance

No obvious unnecessary calls

No blocking work on UI/API request path

Database queries reasonable

Documentation

README/docs updated if necessary

API/schema changes documented

76. DEFINITION OF DONE

A feature is NOT complete merely because code exists.

It is complete when:

implementation is integrated

expected behavior works

error states work

tests pass

build passes

security is checked

relevant documentation is updated

no unrelated functionality was broken

77. ABSOLUTE DO'S

Claude MUST:

read CLAUDE.md first

inspect existing code

reuse existing code where appropriate

keep architecture consistent

write maintainable code

validate inputs

test changes

handle failures

protect secrets

document meaningful architectural changes

distinguish real data from simulated data

distinguish measured results from assumptions

preserve user changes

report actual validation results

78. ABSOLUTE DON'TS

Claude MUST NOT:

invent APIs

invent credentials

invent benchmark numbers

expose secrets

commit .env

silently use fake traffic

claim unsupported real-time behavior

rewrite the whole project unnecessarily

delete working code without reason

ignore tests

suppress errors

silently change optimization objectives

silently change provider behavior

add unnecessary dependencies

create unnecessary microservices

hard-code secrets

make unsupported algorithm claims

discard existing uncommitted work

say "tested" when it was not tested

79. PRIORITY ORDER

When trade-offs occur, use this priority:

Safety and security

Correctness

User requirement

Architecture consistency

Data integrity

Reliability

Testability

Performance

Maintainability

UI polish

Do not sacrifice correctness for speed of implementation.

80. FINAL CLAUDE PROTOCOL

Before every implementation, silently check:

[ ] I read CLAUDE.md. [ ] I understand the requested behavior. [ ]
I inspected the existing repository. [ ] I found reusable code. [ ]
I identified affected layers. [ ] I identified dependencies. [ ] I
considered failure states. [ ] I considered security. [ ] I
considered performance. [ ] I have a minimal implementation plan.

After implementation:

[ ] Code is formatted. [ ] Tests were run. [ ] Build/static checks
were run where applicable. [ ] Integration was verified where
applicable. [ ] Documentation was updated where necessary. [ ] No
unrelated code was changed. [ ] I can explain exactly what changed. [
] I will not claim validation that did not happen.

81. PROJECT NORTH STAR

Every technical decision should move QTrace toward a reliable,
cost-efficient, production-ready logistics optimization platform.

The central product loop is:

Input logistics problem → Validate constraints → Obtain
road/traffic costs → Optimize routes → Evaluate solution →
Return understandable routes → Display on map → Monitor
results → Improve using measured evidence

Do not lose this core purpose by adding unrelated functionality.

82. INSTRUCTION TO FUTURE CLAUDE INSTANCES

You are an engineering agent working inside an existing software
project.

Treat the repository as the source of implementation truth and this
document as the source of project rules.

Do not assume that a generated solution is correct merely because it
compiles.

Inspect first. Plan second. Implement third. Test fourth. Report fifth.

Prefer small, reversible, evidence-based changes over large speculative
rewrites.

When uncertain about a critical requirement, ask.

When the requirement is clear, execute it completely.

When a feature is implemented, leave the repository in a cleaner and
more reliable state than before.

END OF QTRACE MASTER INSTRUCTIONS