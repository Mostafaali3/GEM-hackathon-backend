# Mobile App Integration - Quick Start

## Backend Server
**Base URL:** `http://YOUR_SERVER_IP:8000`

---

## 1. Login/Register User (One Call!)

**Endpoint:** `POST /api/auth/login-register`

**Kotlin Code:**
```kotlin
// Data classes
data class LoginRequest(
    val email: String,
    val name: String?,
    val gender: String?,
    val virtual_nfc_id: String
)

data class LoginResponse(
    val status: String,
    val message: String,
    val user: User,
    val is_new_user: Boolean
)

data class User(
    val id: Int,
    val email: String,
    val name: String?,
    val virtual_nfc_id: String?
)

// Retrofit interface
@POST("api/auth/login-register")
suspend fun loginOrRegister(@Body request: LoginRequest): Response<LoginResponse>

// Usage
fun login() {
    lifecycleScope.launch {
        // Generate virtual NFC ID (do this ONCE and save it)
        val prefs = getSharedPreferences("gem", MODE_PRIVATE)
        var nfcId = prefs.getString("nfc_id", null)
        if (nfcId == null) {
            nfcId = "GEM_${UUID.randomUUID()}"
            prefs.edit().putString("nfc_id", nfcId).apply()
        }
        
        // Make API call
        val response = apiService.loginOrRegister(
            LoginRequest(
                email = "user@example.com",
                name = "User Name",
                gender = null,
                virtual_nfc_id = nfcId
            )
        )
        
        if (response.isSuccessful) {
            val result = response.body()!!
            // Success! User is logged in and NFC is registered
            Log.d("Login", "User ID: ${result.user.id}")
            Log.d("Login", "NFC ID: ${result.user.virtual_nfc_id}")
        }
    }
}
```

---

## 2. Test Gate Authentication

**Endpoint:** `POST /api/gate/scan`

**Kotlin Code:**
```kotlin
data class ScanRequest(val scanned_id: String)
data class ScanResponse(
    val status: String,
    val user_name: String?,
    val welcome_message: String?
)

@POST("api/gate/scan")
suspend fun scanGate(@Body request: ScanRequest): Response<ScanResponse>

// Usage
fun testGateScan() {
    lifecycleScope.launch {
        val nfcId = getSharedPreferences("gem", MODE_PRIVATE)
            .getString("nfc_id", null)!!
        
        val response = apiService.scanGate(ScanRequest(nfcId))
        
        if (response.isSuccessful) {
            val result = response.body()!!
            if (result.status == "ACCESS_GRANTED") {
                Toast.makeText(this, result.welcome_message, Toast.LENGTH_SHORT).show()
            }
        }
    }
}
```

---

## 3. Link Physical Card (Optional)

**Endpoint:** `POST /api/cards/link`

**Kotlin Code:**
```kotlin
data class LinkCardRequest(val user_id: Int, val card_uid: String)
data class LinkCardResponse(
    val status: String,
    val message: String
)

@POST("api/cards/link")
suspend fun linkCard(@Body request: LinkCardRequest): Response<LinkCardResponse>

// Usage
fun linkPhysicalCard(userId: Int, cardUid: String) {
    lifecycleScope.launch {
        val response = apiService.linkCard(
            LinkCardRequest(userId, cardUid)
        )
        
        if (response.isSuccessful) {
            Toast.makeText(this, "Card linked!", Toast.LENGTH_SHORT).show()
        }
    }
}
```

---

## Complete Retrofit Setup

```kotlin
// build.gradle.kts
dependencies {
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.11.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.6.2")
}

// RetrofitClient.kt
object RetrofitClient {
    private const val BASE_URL = "http://YOUR_SERVER_IP:8000/"
    
    private val okHttp = OkHttpClient.Builder()
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        })
        .build()
    
    val api: GemApi = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(okHttp)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(GemApi::class.java)
}

// GemApi.kt
interface GemApi {
    @POST("api/auth/login-register")
    suspend fun loginOrRegister(@Body request: LoginRequest): Response<LoginResponse>
    
    @POST("api/gate/scan")
    suspend fun scanGate(@Body request: ScanRequest): Response<ScanResponse>
    
    @POST("api/cards/link")
    suspend fun linkCard(@Body request: LinkCardRequest): Response<LinkCardResponse>
}
```

---

## Key Points

1. **Generate NFC ID once** - Save it in SharedPreferences, never change it
2. **Use `/api/auth/login-register`** - Single call for login + NFC registration
3. **Test with `/api/gate/scan`** - Verify NFC works
4. **Replace `YOUR_SERVER_IP`** - Use your actual server IP address

That's it! Three endpoints, ready to use.
