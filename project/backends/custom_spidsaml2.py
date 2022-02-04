import logging
import re
import saml2

from saml2.response import StatusAuthnFailed
from saml2.metadata import entity_descriptor
from saml2.sigver import SignatureError
from satosa.backends.saml2 import SAMLBackend
from satosa.context import Context
from satosa.exception import SATOSAAuthenticationError
from satosa.response import Response

from .spidsaml2_validator import Saml2ResponseValidator

from .spidsaml2 import SpidSAMLBackend

logger = logging.getLogger(__name__)


class CustomSpidSAMLBackend(SpidSAMLBackend):

    def authn_response(self, context, binding):
        """
        Endpoint for the idp response
        :type context: satosa.context,Context
        :type binding: str
        :rtype: satosa.response.Response

        :param context: The current context
        :param binding: The saml binding type
        :return: response
        """
        if not context.request["SAMLResponse"]:
            logger.debug("Missing Response for state")
            raise SATOSAAuthenticationError(context.state, "Missing Response")

        try:
            authn_response = self.sp.parse_authn_request_response(
                context.request["SAMLResponse"],
                binding,
                outstanding=self.outstanding_queries,
            )
        except StatusAuthnFailed as err:
            erdict = re.search(r"ErrorCode nr(?P<err_code>\d+)", str(err))
            if erdict:
                return self.handle_spid_anomaly(erdict.groupdict()["err_code"], err)
            else:
                return self.handle_error(
                    **{
                        "err": err,
                        "message": "Autenticazione fallita",
                        "troubleshoot": (
                            "Anomalia riscontrata durante la fase di Autenticazione. "
                            f"{_TROUBLESHOOT_MSG}"
                        ),
                    }
                )
        except SignatureError as err:
            return self.handle_error(
                **{
                    "err": err,
                    "message": "Autenticazione fallita",
                    "troubleshoot": (
                        "La firma digitale della risposta ottenuta "
                        f"non risulta essere corretta. {_TROUBLESHOOT_MSG}"
                    ),
                }
            )
        except Exception as err:
            return self.handle_error(
                **{
                    "err": err,
                    "message": "Anomalia riscontrata nel processo di Autenticazione",
                    "troubleshoot": _TROUBLESHOOT_MSG,
                }
            )

        if self.sp.config.getattr("allow_unsolicited", "sp") is False:
            req_id = authn_response.in_response_to
            if req_id not in self.outstanding_queries:
                errmsg = ("No request with id: {}".format(req_id),)
                logger.debug(errmsg)
                return self.handle_error(
                    **{"message": errmsg, "troubleshoot": _TROUBLESHOOT_MSG}
                )
            del self.outstanding_queries[req_id]

        # Context validation
        if not context.state.get(self.name):
            _msg = f"context.state[self.name] KeyError: where self.name is {self.name}"
            logger.error(_msg)
            return self.handle_error(
                **{"message": _msg, "troubleshoot": _TROUBLESHOOT_MSG}
            )
        # check if the relay_state matches the cookie state
        if context.state[self.name]["relay_state"] != context.request["RelayState"]:
            _msg = "State did not match relay state for state"
            return self.handle_error(
                **{"message": _msg, "troubleshoot": _TROUBLESHOOT_MSG}
            )

        # Spid and SAML2 additional tests
        _sp_config = self.config["sp_config"]
        accepted_time_diff = _sp_config["accepted_time_diff"]
        recipient = _sp_config["service"]["sp"]["endpoints"][
            "assertion_consumer_service"
        ][0][0]
        authn_context_classref = self.config["acr_mapping"][""]

        issuer = authn_response.response.issuer

        # this will get the entity name in state
        if len(context.state.keys()) < 2:
            _msg = "Inconsistent context.state"
            return self.handle_error(
                **{"message": _msg, "troubleshoot": _TROUBLESHOOT_MSG}
            )

        list(context.state.keys())[1]
        # deprecated
        # if not context.state.get('Saml2IDP'):
        # _msg = "context.state['Saml2IDP'] KeyError"
        # logger.error(_msg)
        # raise SATOSAStateError(context.state, "State without Saml2IDP")
        in_response_to = context.state["req_args"]["id"]

        # some debug
        if authn_response.ava:
            logging.debug(
                f"Attributes to {authn_response.return_addrs} "
                f"in_response_to {authn_response.in_response_to}: "
                f'{",".join(authn_response.ava.keys())}'
            )

        validator = Saml2ResponseValidator(
            authn_response=authn_response.xmlstr,
            recipient=recipient,
            in_response_to=in_response_to,
            accepted_time_diff=accepted_time_diff,
            authn_context_class_ref=authn_context_classref,
            return_addrs=authn_response.return_addrs,
            allowed_acrs=self.config["spid_allowed_acrs"],
        )
        try:
            validator.run()
        except Exception as e:
            logger.error(e)
            return self.handle_error(e)

        context.decorate(Context.KEY_BACKEND_METADATA_STORE, self.sp.metadata)
        if self.config.get(SAMLBackend.KEY_MEMORIZE_IDP):
            issuer = authn_response.response.issuer.text.strip()
            context.state[Context.KEY_MEMORIZED_IDP] = issuer
        context.state.pop(self.name, None)
        context.state.pop(Context.KEY_FORCE_AUTHN, None)

        logger.info(f"SAMLResponse{authn_response.xmlstr}")
        return self.auth_callback_func(
            context, self._translate_response(authn_response, context.state)
        )
