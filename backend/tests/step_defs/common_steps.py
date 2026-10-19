from datetime import date

from pytest_bdd import given, parsers, then

from tests.step_defs.world import World


@given(parsers.re(r'today is "(?P<day>[^"]+)"'))
def today_is(world: World, day: str) -> None:
    world.clock.set_today(date.fromisoformat(day))


@given(parsers.re(r'a user "(?P<email>[^"]+)" exists with password "(?P<password>[^"]+)"'))
def user_exists_with_password(world: World, email: str, password: str) -> None:
    world.ensure_user(email, password)


@given(parsers.re(r'a user "(?P<email>[^"]+)" exists'))
def user_exists(world: World, email: str) -> None:
    world.ensure_user(email)


@given(parsers.re(r'I am logged in as "(?P<email>[^"]+)"'))
def logged_in_as(world: World, email: str) -> None:
    world.log_in(email)


@given(parsers.re(r'the user "(?P<email>[^"]+)" is deactivated'))
def user_is_deactivated(world: World, email: str) -> None:
    async def deactivate() -> None:
        async with world.container.unit_of_work() as uow:
            user = await uow.users.get_by_email(email)
            assert user is not None
            user.deactivate()
            await uow.users.save(user)
            await uow.commit()

    world.run(deactivate)


@then(parsers.parse("the response status should be {status:d}"))
def response_status_is(world: World, status: int) -> None:
    assert world.response.status_code == status, world.response.text
