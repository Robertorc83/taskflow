from pytest_bdd import parsers, then, when

from tests.step_defs.world import World


@when(
    parsers.re(
        r'I register with email "(?P<email>[^"]*)", name "(?P<name>[^"]*)"'
        r' and password "(?P<password>[^"]*)"'
    )
)
def register(world: World, email: str, name: str, password: str) -> None:
    world.request(
        "POST",
        "/auth/register",
        anonymous=True,
        json={"email": email, "full_name": name, "password": password},
    )


@when(parsers.re(r'I log in as "(?P<email>[^"]+)" with password "(?P<password>[^"]+)"'))
def log_in(world: World, email: str, password: str) -> None:
    world.request(
        "POST", "/auth/login", anonymous=True, json={"email": email, "password": password}
    )


@when("I request my profile")
def request_profile(world: World) -> None:
    world.request("GET", "/users/me")


@when("I request my profile without a token")
def request_profile_without_token(world: World) -> None:
    world.request("GET", "/users/me", anonymous=True)


@when(parsers.re(r'I request my profile with the token "(?P<token>[^"]+)"'))
def request_profile_with_token(world: World, token: str) -> None:
    world.request("GET", "/users/me", anonymous=True, headers={"Authorization": f"Bearer {token}"})


@when("I refresh my tokens")
def refresh_tokens(world: World) -> None:
    assert world.current_email is not None
    token = world.refresh_tokens[world.current_email]
    world.request("POST", "/auth/refresh", anonymous=True, json={"refresh_token": token})


@when("I try to refresh using my access token")
def refresh_with_access_token(world: World) -> None:
    assert world.current_email is not None
    token = world.access_tokens[world.current_email]
    world.request("POST", "/auth/refresh", anonymous=True, json={"refresh_token": token})


@when("I list the users")
def list_users(world: World) -> None:
    world.request("GET", "/users", params={"size": 100})


@then(parsers.re(r'the response should contain the email "(?P<email>[^"]+)"'))
def response_contains_email(world: World, email: str) -> None:
    assert world.body["email"] == email


@then("the response should not expose the password")
def response_hides_password(world: World) -> None:
    assert not {"password", "hashed_password"} & world.body.keys()


@then("I should receive an access token and a refresh token")
def received_token_pair(world: World) -> None:
    body = world.body
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["access_token"] != body["refresh_token"]


@then(parsers.re(r'the user list should include "(?P<email>[^"]+)"'))
def user_list_includes(world: World, email: str) -> None:
    assert email in {user["email"] for user in world.body["items"]}
