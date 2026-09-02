"""Tests for revert_triplestore_if_possible: the missing-record path must DROP
the triplestore graph URI (RDFidPrefix-prefixed), matching the write paths."""

from flaskapp.storage_utilities.graph import revert_triplestore_if_possible


class TestRevertTriplestoreDeletePath:
    def test_relative_id_prefixed_with_rdfidprefix(self, current_app, mocker):
        # divergent graph and display prefixes
        current_app.config["RDFidPrefix"] = "https://graph.example/ns"
        mocker.patch("flaskapp.storage_utilities.graph.get_record", return_value=None)
        mock_graph_delete = mocker.patch(
            "flaskapp.storage_utilities.graph.graph_delete", return_value=True
        )

        results = revert_triplestore_if_possible(["objects/thing42"], timeout=45)

        # the DROP target is the RDFidPrefix-prefixed graph URI, not the raw id
        call_args = mock_graph_delete.call_args
        assert call_args.args[0] == "https://graph.example/ns/objects/thing42"
        assert call_args.args[0] != f"{current_app.config['idPrefix']}/objects/thing42"
        assert results == {"objects/thing42": "deleted"}

    def test_absolute_id_passes_through_unchanged(self, current_app, mocker):
        current_app.config["RDFidPrefix"] = "https://graph.example/ns"
        mocker.patch("flaskapp.storage_utilities.graph.get_record", return_value=None)
        mock_graph_delete = mocker.patch(
            "flaskapp.storage_utilities.graph.graph_delete", return_value=True
        )

        absolute_id = "https://elsewhere.example/thing"
        results = revert_triplestore_if_possible([absolute_id], timeout=45)

        # client-supplied absolute ids (which idPrefixer skips at write time)
        # must not be re-prefixed
        assert mock_graph_delete.call_args.args[0] == absolute_id
        assert results == {absolute_id: "deleted"}
