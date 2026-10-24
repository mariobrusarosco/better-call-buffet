from types import SimpleNamespace

import pytest

from app.domains.cashflow.views.models import CashflowViewGroup


@pytest.fixture
def tree(ledger):
    """The ledger plus a view with sub-groups and both match kinds:

    Health (parent)
      Mother   all of [health, mother]     Mother appointment, Family pharmacy
      Myself   all of [health, personal]   Family pharmacy, Gym
    Family     any of [mother, personal]   Mother appointment, Family pharmacy,
                                           Gym, Gift for mother

    Family pharmacy is in both sub-groups of Health and carries both tags of
    Family: each total must still count it once.
    """
    tags = ledger.tags
    response = ledger.client.post(
        "/api/v1/cashflow/views",
        json={
            "name": "Monthly",
            "groups": [
                {
                    "name": "Health",
                    "groups": [
                        {
                            "name": "Mother",
                            "match": "all",
                            "tag_ids": [tags["health"], tags["mother"]],
                        },
                        {
                            "name": "Myself",
                            "match": "all",
                            "tag_ids": [tags["health"], tags["personal"]],
                        },
                    ],
                },
                {
                    "name": "Family",
                    "match": "any",
                    "tag_ids": [tags["mother"], tags["personal"]],
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    view = response.json()
    health, family = view["groups"]
    mother, myself = health["groups"]

    return SimpleNamespace(
        **vars(ledger),
        view=view,
        view_url=f"/api/v1/cashflow/views/{view['id']}",
        health=health["id"],
        mother=mother["id"],
        myself=myself["id"],
        family=family["id"],
    )


def test_view_returns_the_nested_tree(tree):
    health, family = tree.view["groups"]

    assert health["match"] is None
    assert health["tag_ids"] == []
    assert [(g["name"], g["match"], g["groups"]) for g in health["groups"]] == [
        ("Mother", "all", []),
        ("Myself", "all", []),
    ]
    assert (family["match"], family["groups"]) == ("any", [])


def test_summary_totals_every_level_counting_each_expense_once(tree):
    response = tree.client.get(f"{tree.view_url}/summary", params=tree.period)

    assert response.status_code == 200
    assert response.json() == {
        "groups": [
            {
                # Mother appointment + Family pharmacy + Gym: 4150, not
                # 4100 + 150, because Family pharmacy is in both sub-groups.
                "group_id": tree.health,
                "total": "4150.00",
                "count": 3,
                "groups": [
                    {
                        "group_id": tree.mother,
                        "total": "4100.00",
                        "count": 2,
                        "groups": [],
                    },
                    {
                        "group_id": tree.myself,
                        "total": "150.00",
                        "count": 2,
                        "groups": [],
                    },
                ],
            },
            {
                # Any of its tags: Gift for mother (mother only) counts.
                "group_id": tree.family,
                "total": "4450.00",
                "count": 4,
                "groups": [],
            },
        ],
        # Only Untagged matches no group that holds tags.
        "ungrouped": {"total": "30.00", "count": 1},
    }


def test_overlaps_never_pair_a_parent_with_its_sub_groups(tree):
    response = tree.client.get(f"{tree.view_url}/overlaps", params=tree.period)

    assert response.status_code == 200
    group_ids_of = {item["description"]: item["group_ids"] for item in response.json()}
    assert group_ids_of == {
        "Family pharmacy": [tree.mother, tree.myself, tree.family],
        "Mother appointment": [tree.mother, tree.family],
        "Gym": [tree.myself, tree.family],
    }


def test_parent_transactions_list_its_sub_groups_expenses_once(tree):
    response = tree.client.get(
        f"{tree.view_url}/groups/{tree.health}/transactions", params=tree.period
    )

    assert response.status_code == 200
    body = response.json()
    assert sorted(t["description"] for t in body["data"]) == [
        "Family pharmacy",
        "Gym",
        "Mother appointment",
    ]
    assert body["meta"]["total"] == 3


def test_sub_group_transactions_list_only_its_own_expenses(tree):
    response = tree.client.get(
        f"{tree.view_url}/groups/{tree.myself}/transactions", params=tree.period
    )

    assert sorted(t["description"] for t in response.json()["data"]) == [
        "Family pharmacy",
        "Gym",
    ]


def test_ungrouped_transactions_follow_the_tree(tree):
    response = tree.client.get(
        f"{tree.view_url}/ungrouped/transactions", params=tree.period
    )

    assert [t["description"] for t in response.json()["data"]] == ["Untagged"]


def test_match_sent_for_a_parent_is_ignored(tree):
    response = tree.client.patch(
        tree.view_url,
        json={
            "groups": [
                {
                    "name": "Health",
                    "match": "all",
                    "groups": [{"name": "Gym", "tag_ids": [tree.tags["personal"]]}],
                }
            ]
        },
    )

    assert response.status_code == 200
    [health] = response.json()["groups"]
    assert health["match"] is None
    assert health["groups"][0]["match"] == "any"


def test_replacing_the_tree_deletes_the_old_sub_groups(tree, db_session):
    response = tree.client.patch(
        tree.view_url,
        json={"groups": [{"name": "Flat", "tag_ids": [tree.tags["health"]]}]},
    )

    assert response.status_code == 200
    remaining = db_session.query(CashflowViewGroup).filter(
        CashflowViewGroup.view_id == tree.view["id"]
    )
    assert [group.name for group in remaining] == ["Flat"]


def test_deleting_the_view_deletes_its_sub_groups(tree, db_session):
    assert tree.client.delete(tree.view_url).status_code == 204

    remaining = db_session.query(CashflowViewGroup).filter(
        CashflowViewGroup.view_id == tree.view["id"]
    )
    assert remaining.count() == 0


# ---- Validation -------------------------------------------------------------------


def leaf(name, tag_id, **extra):
    return {"name": name, "tag_ids": [tag_id], **extra}


@pytest.mark.parametrize(
    "build_groups, code, message",
    [
        (
            lambda tag: [{**leaf("Home", tag), "groups": [leaf("Bills", tag)]}],
            "CASHFLOW_GROUP_TAGS_AND_SUBGROUPS",
            'Group "Home" can hold tags or sub-groups, not both.',
        ),
        (
            lambda tag: [{"name": "Home", "tag_ids": []}],
            "CASHFLOW_GROUP_NEEDS_TAGS_OR_SUBGROUPS",
            'Group "Home" needs tags or sub-groups.',
        ),
        (
            lambda tag: [{"name": "Home", "groups": [{"name": "Bills"}]}],
            "CASHFLOW_GROUP_NEEDS_TAGS_OR_SUBGROUPS",
            'Sub-group "Bills" needs at least one tag.',
        ),
        (
            lambda tag: [
                {
                    "name": "Home",
                    "groups": [{"name": "Bills", "groups": [leaf("Rent", tag)]}],
                }
            ],
            "CASHFLOW_GROUP_TOO_DEEP",
            'Sub-group "Bills" can\'t hold sub-groups.',
        ),
        (
            lambda tag: [leaf("Bills", tag, match="some")],
            "CASHFLOW_GROUP_INVALID_MATCH",
            'Group "Bills" must match "any" or "all" of its tags.',
        ),
        (
            # 10 groups with 4 sub-groups each: 50 is fine, this is 51.
            lambda tag: [
                {"name": f"G{i}", "groups": [leaf(f"S{i}{j}", tag) for j in range(4)]}
                for i in range(10)
            ]
            + [leaf("One too many", tag)],
            "CASHFLOW_VIEW_TOO_MANY_GROUPS",
            "A view can have at most 50 groups, counting sub-groups.",
        ),
    ],
)
def test_invalid_trees_are_rejected_with_a_code_and_message(
    ledger, build_groups, code, message
):
    response = ledger.client.post(
        "/api/v1/cashflow/views",
        json={"name": "V", "groups": build_groups(ledger.tags["health"])},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert (error["code"], error["message"]) == (code, message)


def test_fifty_groups_counting_sub_groups_are_allowed(ledger):
    tag = ledger.tags["health"]
    response = ledger.client.post(
        "/api/v1/cashflow/views",
        json={
            "name": "V",
            "groups": [
                {"name": f"G{i}", "groups": [leaf(f"S{i}{j}", tag) for j in range(4)]}
                for i in range(10)
            ],
        },
    )

    assert response.status_code == 201, response.text
