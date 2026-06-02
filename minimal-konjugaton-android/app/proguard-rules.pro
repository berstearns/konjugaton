# kotlinx.serialization keeps. The library ships consumer rules, but these are
# belt-and-suspenders for our @Serializable DTOs under R8 full mode.
-keepclassmembers class **$$serializer { *; }
-keepclasseswithmembers class * {
    public static **$$serializer *;
}
-keepclassmembers @kotlinx.serialization.Serializable class * {
    *** Companion;
    *** INSTANCE;
}
-keep,includedescriptorclasses class com.konjugaton.hc.**$$serializer { *; }
