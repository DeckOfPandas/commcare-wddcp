from corehq.apps.es.cases import CaseES


def scroll_case_ids_by_domain_and_case_type(domain, case_type, chunk_size=100):
    """
    Retrieves the case ids in chunks, yielding a list of case ids each time
    until there are none left.

    Only filters on domain and case type, and includes both open and closed cases.
    """
    query = (CaseES()
             .domain(domain)
             .case_type(case_type)
             .exclude_source()
             .size(chunk_size))

    result = []

    for case_id in query.scroll():
        if not isinstance(case_id, basestring):
            raise ValueError("Something is wrong with the query, expected ids only")

        result.append(case_id)
        if len(result) >= chunk_size:
            yield result
            result = []

    if result:
        yield result
