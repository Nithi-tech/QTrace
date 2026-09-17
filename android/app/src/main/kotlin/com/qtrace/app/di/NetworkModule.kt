package com.qtrace.app.di

import com.qtrace.app.BuildConfig
import com.qtrace.app.data.api.QTraceApiService
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

/** API base URL is env-driven build config, never hard-coded (CLAUDE.md #18, #35). No provider
 * API keys live in this app - those stay server-side (CLAUDE.md #27). */
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    // Fleet route requests make several sequential upstream calls server-side (one routing
    // matrix call, then one route() call per vehicle used, plus geocoding for any address-only
    // destinations), so this must comfortably exceed that total, not just one hop's latency -
    // 10s was tripping on real multi-vehicle requests before the backend's own per-call timeout
    // (ROUTING_REQUEST_TIMEOUT_SECONDS) was even reached.
    private const val REQUEST_TIMEOUT_SECONDS = 30L

    @Provides
    @Singleton
    fun provideJson(): Json = Json { ignoreUnknownKeys = true; isLenient = true }

    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BASIC else HttpLoggingInterceptor.Level.NONE
        }
        return OkHttpClient.Builder()
            .connectTimeout(REQUEST_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .readTimeout(REQUEST_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(client: OkHttpClient, json: Json): Retrofit =
        Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()

    @Provides
    @Singleton
    fun provideApiService(retrofit: Retrofit): QTraceApiService = retrofit.create(QTraceApiService::class.java)
}
