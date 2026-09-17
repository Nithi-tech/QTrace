package com.qtrace.app.di

import com.qtrace.app.data.network.AndroidConnectivityObserver
import com.qtrace.app.data.network.ConnectivityObserver
import com.qtrace.app.data.repository.FleetRepositoryImpl
import com.qtrace.app.data.repository.GeocodingRepositoryImpl
import com.qtrace.app.data.repository.RouteRepositoryImpl
import com.qtrace.app.data.repository.TrackingRepositoryImpl
import com.qtrace.app.domain.repository.FleetRepository
import com.qtrace.app.domain.repository.GeocodingRepository
import com.qtrace.app.domain.repository.RouteRepository
import com.qtrace.app.domain.repository.TrackingRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {

    @Binds
    @Singleton
    abstract fun bindGeocodingRepository(impl: GeocodingRepositoryImpl): GeocodingRepository

    @Binds
    @Singleton
    abstract fun bindRouteRepository(impl: RouteRepositoryImpl): RouteRepository

    @Binds
    @Singleton
    abstract fun bindFleetRepository(impl: FleetRepositoryImpl): FleetRepository

    @Binds
    @Singleton
    abstract fun bindConnectivityObserver(impl: AndroidConnectivityObserver): ConnectivityObserver

    @Binds
    @Singleton
    abstract fun bindTrackingRepository(impl: TrackingRepositoryImpl): TrackingRepository
}
