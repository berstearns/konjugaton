/*
 * The catalog: all loaded reference data, indexed for the engine.
 *
 * Port of the `Catalog` aggregate from konjugaton's `data/loader.py`. Pure — the
 * actual JSON parsing lives in the data layer (data/Loader.kt), keeping the
 * domain free of any I/O or serialization concern.
 */
package com.konjugaton.hc.domain

class Catalog(
    val verbs: Map<String, Verb>,
    val endings: EndingTables,
    val contexts: Map<String, SemanticContext>,
) {
    fun verb(lemma: String): Verb = verbs.getValue(lemma)

    val lemmas: List<String> get() = verbs.keys.toList()
    val contextIds: List<String> get() = contexts.keys.toList()
}
