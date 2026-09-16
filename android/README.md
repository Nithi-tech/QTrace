# QTrace Android

First production route-planning screen: map + start/destination search + road route +
optimization result. See [../CLAUDE.md](../CLAUDE.md) for the full architecture rules this
module follows.

## Architecture

```
ui/            Compose screens, reusable components, theme, navigation
domain/        Coordinate/RouteInfo/OptimizationResult models, repository interfaces, QTraceError
data/          Retrofit API + DTOs, repository implementations, DTO<->domain mappers, connectivity
di/            Hilt modules (network, repository bindings)
```

MVVM/UDF: `RoutePlanningScreen` renders `RoutePlanningState` and emits `RoutePlanningEvent`;
`RoutePlanningViewModel` holds all logic; repositories are the only thing that talks to
Retrofit. No business logic lives in a Composable (CLAUDE.md #14).

## Configuration

Two build-time values are read from `local.properties` (gitignored, never commit):

```properties
sdk.dir=/path/to/android-sdk
qtrace.apiBaseUrl=http://10.0.2.2:8000/   # backend base URL; 10.0.2.2 reaches the host from an emulator
qtrace.mapStyleUrl=https://tiles.openfreemap.org/styles/liberty
```

Neither is a secret - the app never contains a TomTom/MapTiler API key or any other provider
credential (CLAUDE.md #27); those stay server-side.

## Map style

The default style is [OpenFreeMap](https://openfreemap.org) "Liberty" - free, keyless, no
account needed. No MapTiler key is configured anywhere in this project yet; if one is added
later, swap `qtrace.mapStyleUrl` to a MapTiler style URL and nothing else needs to change
(CLAUDE.md #34 - the provider is abstracted behind one config value, not hard-coded).

**Known limitation:** there is currently only one style URL, used for both light and dark
theme. A distinct dark map style (CLAUDE.md #8) is not wired in yet.

## Running

```bash
./gradlew :app:assembleDebug   # or: gradle :app:assembleDebug if the wrapper can't reach network
```

Requires JDK 17 and Android SDK Platform 35 + Build-Tools 35.0.0.

## Known limitations / next steps

- Map-tap location selection is not implemented (CLAUDE.md #11 explicitly allows deferring this
  to a future enhancement rather than adding it speculatively now).
- Start/destination markers use simple generated circle icons, not a branded pin asset.
- The classic MapLibre Annotations API (`MarkerOptions`/`addMarker`) used for markers is
  deprecated upstream in favor of GeoJSON `SymbolLayer`; it still works correctly in the
  MapLibre version pinned here but is a candidate for a follow-up migration.
- No emulator/on-device manual verification has been performed in the environment this was
  built in (no emulator available) - only a real Gradle compile, `assembleDebug`, unit tests, and
  lint were run. See the conversation's final report for exactly what was and wasn't verified.
