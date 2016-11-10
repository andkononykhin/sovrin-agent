import logging
import aiohttp_cors
import sockjs
import json

from jsonschema import ValidationError
from aiohttp.web import Application

from plenum.common.looper import Looper
from plenum.common.signer_simple import SimpleSigner
from sovrin.client.wallet.wallet import Wallet
from sovrin.agent.agent import runAgent, WalletedAgent
from sovrin.client.client import Client

from agent.api.middlewares.jsonParseMiddleware import jsonParseMiddleware
from agent.common.signatureValidation import SignatureError
from agent.onboarding.api.onboard import onboard
from agent.login.api.login import login
from agent.links.api.invitation import acceptInvitation
from agent.claims.api.claims import getClaim
from agent.common.apiMessages import SOCKET_CONNECTED, SOCKET_CLOSED
from agent.common.errorMessages import INVALID_DATA

log = logging.getLogger()


async def handleWebSocketRequest(data, app):
    # TODO:SC Add version in route as well
    routeMap = {
        'acceptInvitation': acceptInvitation,
        'getClaim': getClaim,
        'login': login,
        'register': onboard
    }
    try:
        return await routeMap[data['route']](data, app)
    except SignatureError as err:
        print(err)
    except (TypeError, KeyError, ValidationError) as err:
        return INVALID_DATA


async def webSocketConnectionHandler(msg, session):
    if msg.tp == sockjs.MSG_OPEN:
        session.manager.broadcast(SOCKET_CONNECTED)
    elif msg.tp == sockjs.MSG_MESSAGE:
        # TODO:SC handle json parse error, schema error
        requestData = json.loads(msg.data)
        responseData = await handleWebSocketRequest(requestData, session.registry)
        session.manager.broadcast(responseData)
    elif msg.tp == sockjs.MSG_CLOSED:
        session.manager.broadcast(SOCKET_CLOSED)


def startAgent(name, seed):

    class ApiAgent(WalletedAgent):
        def __init__(self,
                     basedirpath: str,
                     client: Client = None,
                     wallet: Wallet = None,
                     port: int = None):
            super().__init__(name, basedirpath, client, wallet, port)

    agentWallet = Wallet(name)
    agentWallet.addIdentifier(signer=SimpleSigner(seed=bytes(seed, 'utf-8')))
    agent = runAgent(ApiAgent, name, wallet=agentWallet, startRunning=False)
    agentPort = agent.endpoint.stackParams['ha'].port
    with Looper(debug=True) as looper:
        looper.add(agent)
        log.debug("Running {} now (port: {})".format(name, agentPort))

    return agent


def api(loop, name, seed):
    app = Application(loop=loop, middlewares=[jsonParseMiddleware])
    sockjs.add_endpoint(app, prefix='/v1/wsConnection', handler=webSocketConnectionHandler)

    # Enable CORS on all APIs
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    for route in list(app.router.routes()):
        if route.name is not None and not route.name.startswith('sock'):
            cors.add(route)

    agent = startAgent(name, seed)
    # Add agent to app instance to allow it to be accessible
    # from all api requests
    app['agent'] = agent
    # In memory list of registered users,
    # not using any database intentionally
    # because we would evernym login/register flow without any database
    # using Everauth of Evernym
    app['users'] = set()

    return app
