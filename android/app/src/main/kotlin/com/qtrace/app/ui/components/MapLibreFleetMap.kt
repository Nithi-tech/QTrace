package com.qtrace.app.ui.components

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color as AndroidColor
import android.graphics.Paint
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.qtrace.app.R
import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.VehicleRouteResult
import org.maplibre.android.annotations.IconFactory
import org.maplibre.android.annotations.MarkerOptions
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.geometry.LatLngBounds
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style
import org.maplibre.android.style.layers.LineLayer
import org.maplibre.android.style.layers.Property
import org.maplibre.android.style.layers.PropertyFactory
import org.maplibre.android.style.sources.GeoJsonSource
import org.maplibre.geojson.Feature
import org.maplibre.geojson.LineString
import org.maplibre.geojson.Point

private const val MAX_ROUTE_LAYERS = 32
private const val CAMERA_PADDING_PX = 120
private const val MARKER_RADIUS_PX = 16f
private const val DEPOT_RADIUS_PX = 20f
private const val MARKER_DIAMETER_PX = 44
private const val DEPOT_DIAMETER_PX = 52

/** A fixed, colorblind-friendlier palette, cycled by vehicle index so each route on the map
 * (and its legend entry) is visually distinct regardless of how many vehicles are used. */
val FLEET_ROUTE_COLORS = listOf(
    "#1B5E44", "#B5560B", "#1F5FA8", "#8E2C8F", "#C4271B",
    "#0F766E", "#7C3AED", "#B45309", "#0369A1", "#4D7C0F",
)

fun colorForVehicle(index: Int): String = FLEET_ROUTE_COLORS[index % FLEET_ROUTE_COLORS.size]

/**
 * Multi-vehicle map: one depot marker, all destination markers, and one distinctly-colored
 * polyline per vehicle route (spec section 10 - "show each vehicle's route separately, use
 * distinct route colors"). Provider-specific rendering stays entirely inside this component,
 * matching MapLibreRouteMap's separation (CLAUDE.md #7/#13/#17).
 */
@Composable
fun MapLibreFleetMap(
    styleUrl: String,
    depot: Coordinate?,
    destinations: List<Coordinate>,
    vehicleRoutes: List<VehicleRouteResult>,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val mapView = remember { MapView(context) }

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

    val contentDescriptionLabel = stringResource(R.string.content_description_fleet_map)

    AndroidView(
        factory = { mapView.apply { contentDescription = contentDescriptionLabel } },
        modifier = modifier,
        update = { view ->
            view.getMapAsync { maplibreMap ->
                maplibreMap.setStyle(Style.Builder().fromUri(styleUrl)) { style ->
                    renderRoutes(style, vehicleRoutes)
                    renderMarkers(context, maplibreMap, depot, destinations)
                    fitCamera(maplibreMap, depot, destinations, vehicleRoutes)
                }
            }
        },
    )
}

private fun renderRoutes(style: Style, vehicleRoutes: List<VehicleRouteResult>) {
    for (i in 0 until MAX_ROUTE_LAYERS) {
        style.getLayer("qtrace-fleet-route-layer-$i")?.let { style.removeLayer(it) }
        style.getSource("qtrace-fleet-route-source-$i")?.let { style.removeSource(it) }
    }

    vehicleRoutes.forEachIndexed { index, route ->
        if (route.geometry.size < 2) return@forEachIndexed
        val points = route.geometry.map { Point.fromLngLat(it.longitude, it.latitude) }
        val source = GeoJsonSource(
            "qtrace-fleet-route-source-$index",
            Feature.fromGeometry(LineString.fromLngLats(points)),
        )
        style.addSource(source)
        style.addLayer(
            LineLayer("qtrace-fleet-route-layer-$index", "qtrace-fleet-route-source-$index").withProperties(
                PropertyFactory.lineColor(AndroidColor.parseColor(colorForVehicle(index))),
                PropertyFactory.lineWidth(5f),
                PropertyFactory.lineCap(Property.LINE_CAP_ROUND),
                PropertyFactory.lineJoin(Property.LINE_JOIN_ROUND),
            ),
        )
    }
}

private fun renderMarkers(
    context: Context,
    maplibreMap: org.maplibre.android.maps.MapLibreMap,
    depot: Coordinate?,
    destinations: List<Coordinate>,
) {
    maplibreMap.markers.toList().forEach { maplibreMap.removeMarker(it) }

    depot?.let {
        maplibreMap.addMarker(
            MarkerOptions()
                .position(LatLng(it.latitude, it.longitude))
                .icon(circleIcon(context, color = AndroidColor.BLACK, diameter = DEPOT_DIAMETER_PX, radius = DEPOT_RADIUS_PX)),
        )
    }
    destinations.forEach { destination ->
        maplibreMap.addMarker(
            MarkerOptions()
                .position(LatLng(destination.latitude, destination.longitude))
                .icon(circleIcon(context, color = AndroidColor.parseColor("#546E7A"), diameter = MARKER_DIAMETER_PX, radius = MARKER_RADIUS_PX)),
        )
    }
}

private fun fitCamera(
    maplibreMap: org.maplibre.android.maps.MapLibreMap,
    depot: Coordinate?,
    destinations: List<Coordinate>,
    vehicleRoutes: List<VehicleRouteResult>,
) {
    val routePoints = vehicleRoutes.flatMap { it.geometry }
    val points = (routePoints.ifEmpty { listOfNotNull(depot) + destinations })
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

private fun circleIcon(context: Context, color: Int, diameter: Int, radius: Float) = IconFactory.getInstance(context).fromBitmap(
    Bitmap.createBitmap(diameter, diameter, Bitmap.Config.ARGB_8888).apply {
        val canvas = Canvas(this)
        val center = diameter / 2f
        canvas.drawCircle(center, center, radius, Paint(Paint.ANTI_ALIAS_FLAG).apply { this.color = color })
        canvas.drawCircle(
            center,
            center,
            radius,
            Paint(Paint.ANTI_ALIAS_FLAG).apply {
                this.color = AndroidColor.WHITE
                style = Paint.Style.STROKE
                strokeWidth = 4f
            },
        )
    },
)
