pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral() // MapLibre Android SDK (org.maplibre.gl:android-sdk) is published here (CLAUDE.md #13)
    }
}

rootProject.name = "QTrace"
include(":app")
