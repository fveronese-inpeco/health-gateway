<%@ taglib uri="http://www.springframework.org/tags" prefix="spring" %>
<%@ taglib uri="urn:mace:shibboleth:2.0:idp:ui" prefix="idpui" %>
<%@ page import="javax.servlet.http.Cookie" %>
<%@ page import="org.opensaml.profile.context.ProfileRequestContext" %>
<%@ page import="net.shibboleth.idp.authn.ExternalAuthentication" %>
<%@ page import="net.shibboleth.idp.authn.context.AuthenticationContext" %>
<%@ page import="net.shibboleth.idp.profile.context.RelyingPartyContext" %>
<%@ page import="net.shibboleth.idp.ui.context.RelyingPartyUIContext" %>

<%
final Cookie[] cookies = request.getCookies();
if (cookies != null) {
    for (final Cookie cookie : cookies) {
        if (cookie.getName().equals("x509passthrough")) {
        	response.sendRedirect(request.getContextPath() + "/Authn/X509?"
                + ExternalAuthentication.CONVERSATION_KEY + "="
                + request.getParameter(ExternalAuthentication.CONVERSATION_KEY));
        	return;
        }
    }
}

final String key = ExternalAuthentication.startExternalAuthentication(request);
final ProfileRequestContext prc = ExternalAuthentication.getProfileRequestContext(key, request);
final AuthenticationContext authnContext = prc.getSubcontext(AuthenticationContext.class);
final RelyingPartyContext rpContext = prc.getSubcontext(RelyingPartyContext.class);
final RelyingPartyUIContext rpUIContext = authnContext.getSubcontext(RelyingPartyUIContext.class);
final boolean identifiedRP = rpUIContext != null && !rpContext.getRelyingPartyId().contains(rpUIContext.getServiceName());
%>


<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>
    <title><spring:message code="idp.title" text="Web Login Service" /></title>
    <link rel="stylesheet" type="text/css" href="<%= request.getContextPath()%>/css/bootstrap.css">
  </head>

  <body>
    <div class="wrapper">
      <div class="container">
        <!--header>
          <img src="<%= request.getContextPath() %><spring:message code="idp.logo" />" alt="<spring:message code="idp.logo.alt-text" text="logo" />">
        </header-->

        <div class="content">
          <div class="column one">
            <form id="loginform" action="<%= request.getContextPath() %>/Authn/X509" method="post">

            <input type="hidden" name="<%= ExternalAuthentication.CONVERSATION_KEY %>"
                value="<%= request.getParameter(ExternalAuthentication.CONVERSATION_KEY) %>">

              <% if (identifiedRP) { %>
                <legend>
                  <spring:message code="idp.login.loginTo" text="Login to" /> <idpui:serviceName uiContext="<%= rpUIContext %>"/>
                </legend>
              <% } %>

              <div class="container">
              <h2 align = "center">TS/CNS Login Authentication Page</h2>
                <div class="panel panel-default">
                    <div class="panel-heading">TS/CNS Identification</div>
                    <div class="panel-body">
                        Ensure you have your TS/CNS reader properly connected and with the required rivers installed.
                        Insert your TS/CNS card into the reader, then click on the TS/CNS Login button. You will be asked
                        to enter your PIN and to confirm certificate selection.
                    </div>
                </div>
              </div>
              <br/>
              <!--section>
                <div class="form-element-wrapper">
                <input type="checkbox" name="<%= ExternalAuthentication.REVOKECONSENT_KEY %>" value="true">
                <spring:message code="idp.attribute-release.revoke"
                    text="Clear prior granting of permission for release of your information to this service." />
                </div>
                <div class="form-element-wrapper">
                <input type="checkbox" name="x509passthrough" value="true" tabindex="2">
                Do not show this page in the future.
                </div>
                <div class="form-element-wrapper">
                <button class="form-element form-button" type="submit" name="login" value="1"
                    tabindex="1" accesskey="l">TS/CNS Login</button>
                </div>
              </section-->
              <div class="form-element-wrapper col-sm-4 col-sm-offset-4 text-center">
                <button class="form-element form-button" type="submit" name="login" value="1"
                    tabindex="1" accesskey="l">TS/CNS Login</button>
              </div>

            </form>

             <%
              //
              //    SP Description & Logo (optional)
              //    These idpui lines will display added information (if available
              //    in the metadata) about the Service Provider (SP) that requested
              //    authentication. These idpui lines are "active" in this example
              //    (not commented out) - this extra SP info will be displayed.
              //    Remove or comment out these lines to stop the display of the
              //    added SP information.
              //
              //    Documentation:
              //      https://wiki.shibboleth.net/confluence/display/SHIB2/IdPAuthUserPassLoginPage
              //
              //    Example:
             %>
             <% if (identifiedRP) { %>
                 <p>
                   <idpui:serviceLogo uiContext="<%= rpUIContext %>">default</idpui:serviceLogo>
                   <idpui:serviceDescription uiContext="<%= rpUIContext %>">SP description</idpui:serviceDescription>
                 </p>
             <% } %>

          </div>
          <!--div class="column two">
            <ul class="list list-help">
              <li class="list-help-item"><a href="#"><span class="item-marker">&rsaquo;</span> Need Help?</a></li>
              <li class="list-help-item"><a href="https://wiki.shibboleth.net/confluence/display/SHIB2/IdPAuthUserPassLoginPage"><span class="item-marker">&rsaquo;</span> How to Customize this Skin</a></li>
            </ul>
          </div-->
        </div>
      </div>

      <!--footer>
        <div class="container container-footer">
          <p class="footer-text"><spring:message code="root.footer" text="Insert your footer text here." /></p>
        </div>
      </footer-->
    </div>

  </body>
</html>
