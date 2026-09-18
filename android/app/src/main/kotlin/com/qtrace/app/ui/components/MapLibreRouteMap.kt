package com.qtrace.app.ui.components

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color as AndroidColor
import android.graphics.Paint
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.qtrace.app.R
import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.MapBounds
import com.qtrace.app.domain.model.TrafficSegment
import org.maplibre.android.annotations.IconFactory
import org.maplibre.android.annotations.MarkerOptions
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.geometry.LatLngBounds
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.Style
import org.maplibre.android.style.expressions.Expression
import org.maplibre.android.style.layers.LineLayer
import org.maplibre.android.style.layers.PropertyFactory
import org.maplibre.android.style.sources.GeoJsonSource
import org.maplibre.geojson.Feature
import org.maplibre.geojson.FeatureCollection
import org.maplibre.geojson.LineString
import org.maplibre.geojson.Point

private const val ROUTE_SOURCE_ID = "qtrace-route-source"
private const val ROUTE_LAYER_ID = "qtrace-route-layer"
private const val TRAFFIC_SOURCE_ID = "qtrace-traffic-source"
private const val TRAFFIC_LAYER_ID = "qtrace-traffic-layer"
private const val TRAFFIC_LEVEL_PROPERTY = "level"
private const val CAMERA_PADDING_PX = 120
private const val MARKER_RADIUS_PX = 18f

/** QTrace's own Google-Maps-style 5-level palette (docs/TRAFFIC_ARCHITECTURE.md) - not
 * Google's colors or assets, just the same familiar traffic-light convention. Levels with
 * no real data (UNKNOWN) are simply absent from this map and never colored. */
private val TRAFFIC_LEVEL_COLORS = linkedMapOf(
    "FREE_FLOW" to "#2E7D32",
    "MODERATE" to "#F9A825",
    "HEAVY" to "#EF6C00",
    "VERY_HEAVY" to "#D32F2F",
    "SEVERE" to "#6A1B1A",
)

/**
 * MapLibre map rendering the planned route and, optionally, a live traffic color overlay
 * (CLAUDE.md #7/#13/#17, docs/TRAFFIC_ARCHITECTURE.md). Provider-specific rendering logic
 * (MapLibre annotations/GeoJSON layers) stays entirely inside this component - the ViewModel
 * and screen only pass plain domain values. Layer order (bottom to top): basemap -> traffic
 * -> route -> markers, so traffic never hides the selected route (CLAUDE.md traffic
 * master-prompt #12).
 */
@Composable
fun MapLibreRouteMap(
    styleUrl: String,
    startLocation: Coordinate?,
    destinationLocation: Coordinate?,
    routeGeometry: List<Coordinate>,
    modifier: Modifier = Modifier,
    trafficEnabled: Boolean = false,
    trafficSegments: List<TrafficSegment> = emptyList(),
    onVisibleBoundsChanged: (MapBounds) -> Unit = {},
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val mapView = remember { MapView(context) }
    val onVisibleBoundsChangedState = rememberUpdatedState(onVisibleBoundsChanged)

    DisposableEffect(lifecycleOwner, mapView) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_CREATE -> mapView.onCreate(null)
                Lifecycle.Event.ON_START -> mapView.onStart()
                Lifecycle.Event.ON_RESUME -> mapView.onResume()
                Lifecycle.Event.ON_PAUSE -> mapView.onPause()
                Lifecycle.Event.ON_STOP -> mapView.onStop()
                Lifecycle.Event.ON_DESTROY -> mapView.onDestroy()
                else -> Unit
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    // Registered exactly once per MapView instance (not on every recomposition) so panning
    // never accumulates duplicate listeners (CLAUDE.md traffic master-prompt #32/#33).
    DisposableEffect(mapView) {
        var registeredMap: MapLibreMap? = null
        val listener = MapLibreMap.OnCameraIdleListener {
            registeredMap?.let { onVisibleBoundsChangedState.value(it.projection.visibleRegion.latLngBounds.toDomain()) }
        }
        mapView.getMapAsync { maplibreMap ->
            registeredMap = maplibreMap
            maplibreMap.addOnCameraIdleListener(listener)
        }
        onDispose { registeredMap?.removeOnCameraIdleListener(listener) }
    }

    val contentDescriptionLabel = stringResource(R.string.content_description_map)

    AndroidView(
        factory = { mapView.apply { contentDescription = contentDescriptionLabel } },
        modifier = modifier,
        update = { view ->
            view.getMapAsync { maplibreMap ->
                maplibreMap.setStyle(Style.Builder().fromUri(styleUrl)) { style ->
                    renderTraffic(style, trafficSegments, trafficEnabled)
                    renderRoute(context, maplibreMap, style, routeGeometry)
                    renderMarkers(context, maplibreMap, startLocation, destinationLocation)
                    fitCamera(maplibreMap, startLocation, destinationLocation, routeGeometry)
                }
            }
        },
    )
}

private fun LatLngBounds.toDomain(): MapBounds = MapBounds(
    minLatitude = latitudeSouth,
    minLongitude = longitudeWest,
    maxLatitude = latitudeNorth,
    maxLongitude = longitudeEast,
)

private fun renderTraffic(style: Style, segments: List<TrafficSegment>, enabled: Boolean) {
    style.getLayer(TRAFFIC_LAYER_ID)?.let { style.removeLayer(it) }
    style.getSource(TRAFFIC_SOURCE_ID)?.let { style.removeSource(it) }

    if (!enabled || segments.isEmpty()) return

    val features = segments.mapNotNull { segment ->
        if (segment.geometry.size < 2) return@mapNotNull null
        val points = segment.geometry.map { Point.fromLngLat(it.longitude, it.latitude) }
        Feature.fromGeometry(LineString.fromLngLats(points)).apply {
            addStringProperty(TRAFFIC_LEVEL_PROPERTY, segment.level.name)
        }
    }
    if (features.isEmpty()) return

    style.addSource(GeoJsonSource(TRAFFIC_SOURCE_ID, FeatureCollection.fromFeatures(features)))

    val colorStops = TRAFFIC_LEVEL_COLORS.map { (level, hex) ->
        Expression.stop(level, Expression.color(AndroidColor.parseColor(hex)))
    }
    style.addLayer(
        LineLayer(TRAFFIC_LAYER_ID, TRAFFIC_SOURCE_ID).withProperties(
            PropertyFactory.lineColor(
                Expression.match(
                    Expression.get(TRAFFIC_LEVEL_PROPERTY),
                    Expression.color(AndroidColor.parseColor(TRAFFIC_LEVEL_COLORS.getValue("FREE_FLOW"))),
                    *colorStops.toTypedArray(),
                ),
            ),
            // Thin at city-wide zoom, thick enough to read once zoomed into a neighborhood
            // (CLAUDE.md traffic master-prompt #13) - never one fixed width at every scale.
            PropertyFactory.lineWidth(
                Expression.interpolate(
                    Expression.linear(),
                    Expression.zoom(),
                    Expression.stop(8, 1.5f),
                    Expression.stop(12, 3f),
                    Expression.stop(14, 5f),
                    Expression.stop(16, 7f),
                ),
            ),
            PropertyFactory.lineCap(org.maplibre.android.style.layers.Property.LINE_CAP_ROUND),
            PropertyFactory.lineJoin(org.maplibre.android.style.layers.Property.LINE_JOIN_ROUND),
            PropertyFactory.lineOpacity(0.85f),
        ),
    )
}

private fun renderRoute(
    context: Context,
    maplibreMap: org.maplibre.android.maps.MapLibreMap,
    style: Style,
    routeGeometry: List<Coordinate>,
) {
    style.getLayer(ROUTE_LAYER_ID)?.let { style.removeLayer(it) }
    style.getSource(ROUTE_SOURCE_ID)?.let { style.removeSource(it) }

    if (routeGeometry.size < 2) return

    val points = routeGeometry.map { Point.fromLngLat(it.longitude, it.latitude) }
    val source = GeoJsonSource(ROUTE_SOURCE_ID, Feature.fromGeometry(LineString.fromLngLats(points)))
    style.addSource(source)

    val routeColor = androidx.core.content.ContextCompat.getColor(context, android.R.color.holo_green_dark)
    style.addLayer(
        LineLayer(ROUTE_LAYER_ID, ROUTE_SOURCE_ID).withProperties(
            PropertyFactory.lineColor(routeColor),
            PropertyFactory.lineWidth(5f),
            PropertyFactory.lineCap(org.maplibre.android.style.layers.Property.LINE_CAP_ROUND),
            PropertyFactory.lineJoin(org.maplibre.android.style.layers.Property.LINE_JOIN_ROUND),
        ),
    )
}

private fun renderMarkers(
    context: Context,
    maplibreMap: org.maplibre.android.maps.MapLibreMap,
    startLocation: Coordinate?,
    destinationLocation: Coordinate?,
) {
    maplibreMap.markers.toList().forEach { maplibreMap.removeMarker(it) }

    startLocation?.let {
        maplibreMap.addMarker(
            MarkerOptions()
                .position(LatLng(it.latitude, it.longitude))
                .icon(circleIcon(context, color = AndroidColor.parseColor("#1B5E44"))),
        )
    }
    destinationLocation?.let {
        maplibreMap.addMarker(
            MarkerOptions()
                .position(LatLng(it.latitude, it.longitude))
                .icon(circleIcon(context, color = AndroidColor.parseColor("#B5560B"))),
        )
    }
}

private fun fitCamera(
    maplibreMap: org.maplibre.android.maps.MapLibreMap,
    startLocation: Coordinate?,
    destinationLocation: Coordinate?,
    routeGeometry: List<Coordinate>,
) {
    val points = (routeGeometry.ifEmpty { listOfNotNull(startLocation, destinationLocation) })
    if (points.size < 2) {
        points.singleOrNull()?.let {
            maplibreMap.moveCamera(CameraUpdateFactory.newLatLngZoom(LatLng(it.latitude, it.longitude), 12.0))
        }
        return
    }

    val bounds = LatLngBounds.Builder().apply {
        points.forEach { include(LatLng(it.latitude, it.longitude)) }
    }.build()

    maplibreMap.moveCamera(CameraUpdateFactory.newLatLngBounds(bounds, CAMERA_PADDING_PX))
}

/** A simple filled circle marker icon - visually distinct start/destination colors, no external
 * asset dependency. Kept intentionally simple; a branded pin asset can replace this later. */
private fun circleIcon(context: Context, color: Int) = IconFactory.getInstance(context).fromBitmap(
    Bitmap.createBitmap(MARKER_DIAMETER_PX, MARKER_DIAMETER_PX, Bitmap.Config.ARGB_8888).apply {
        val canvas = Canvas(this)
        val center = MARKER_DIAMETER_PX / 2f
        canvas.drawCircle(center, center, MARKER_RADIUS_PX, Paint(Paint.ANTI_ALIAS_FLAG).apply { this.color = color })
        canvas.drawCircle(
            center,
            center,
            MARKER_RADIUS_PX,
            Paint(Paint.ANTI_ALIAS_FLAG).apply {
                this.color = AndroidColor.WHITE
                style = Paint.Style.STROKE
                strokeWidth = 4f
            },
        )
    },
)

private const val MARKER_DIAMETER_PX = 48
