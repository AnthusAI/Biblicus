import {
  ADD_OAUTH_LISTENER,
  AMPLIFY_SYMBOL,
  Amplify,
  AmplifyError,
  AmplifyErrorCode,
  AmplifyUrl,
  AuthAction,
  Category,
  ConsoleLogger,
  CookieStorage,
  Hub,
  Sha256,
  USER_AGENT_HEADER,
  WordArray,
  assertIdentityPoolIdConfig,
  assertOAuthConfig,
  assertTokenProviderConfig,
  base64Decoder,
  base64Encoder,
  cognitoIdentityPoolEndpointResolver,
  composeServiceApi,
  composeTransferHandler,
  createAssertionFunction,
  createGetCredentialsForIdentityClient,
  createGetIdClient,
  deDupeAsyncFunction,
  decodeJWT,
  defaultStorage,
  getAmplifyUserAgent,
  getDeviceName,
  getDnsSuffix,
  getRetryDecider,
  isBrowser,
  isTokenExpired,
  jitteredBackoff,
  parseAmplifyConfig,
  parseJsonBody,
  parseJsonError,
  syncSessionStorage,
  unauthenticatedHandler,
  urlSafeDecode
} from "./chunk-UFPSZHE6.js";
import "./chunk-G3PMV62Z.js";

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/errors/types/validation.mjs
var AuthValidationErrorCode;
(function(AuthValidationErrorCode2) {
  AuthValidationErrorCode2["EmptySignInUsername"] = "EmptySignInUsername";
  AuthValidationErrorCode2["EmptySignInPassword"] = "EmptySignInPassword";
  AuthValidationErrorCode2["CustomAuthSignInPassword"] = "CustomAuthSignInPassword";
  AuthValidationErrorCode2["EmptySignUpUsername"] = "EmptySignUpUsername";
  AuthValidationErrorCode2["EmptySignUpPassword"] = "EmptySignUpPassword";
  AuthValidationErrorCode2["EmptyConfirmSignUpUsername"] = "EmptyConfirmSignUpUsername";
  AuthValidationErrorCode2["EmptyConfirmSignUpCode"] = "EmptyConfirmSignUpCode";
  AuthValidationErrorCode2["EmptyResendSignUpCodeUsername"] = "EmptyresendSignUpCodeUsername";
  AuthValidationErrorCode2["EmptyChallengeResponse"] = "EmptyChallengeResponse";
  AuthValidationErrorCode2["EmptyConfirmResetPasswordUsername"] = "EmptyConfirmResetPasswordUsername";
  AuthValidationErrorCode2["EmptyConfirmResetPasswordNewPassword"] = "EmptyConfirmResetPasswordNewPassword";
  AuthValidationErrorCode2["EmptyConfirmResetPasswordConfirmationCode"] = "EmptyConfirmResetPasswordConfirmationCode";
  AuthValidationErrorCode2["EmptyResetPasswordUsername"] = "EmptyResetPasswordUsername";
  AuthValidationErrorCode2["EmptyVerifyTOTPSetupCode"] = "EmptyVerifyTOTPSetupCode";
  AuthValidationErrorCode2["EmptyConfirmUserAttributeCode"] = "EmptyConfirmUserAttributeCode";
  AuthValidationErrorCode2["IncorrectMFAMethod"] = "IncorrectMFAMethod";
  AuthValidationErrorCode2["EmptyUpdatePassword"] = "EmptyUpdatePassword";
  AuthValidationErrorCode2["InvalidPreferredChallenge"] = "InvalidPreferredChallenge";
})(AuthValidationErrorCode || (AuthValidationErrorCode = {}));

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/common/AuthErrorStrings.mjs
var validationErrorMap = {
  [AuthValidationErrorCode.EmptyChallengeResponse]: {
    message: "challengeResponse is required to confirmSignIn"
  },
  [AuthValidationErrorCode.EmptyConfirmResetPasswordUsername]: {
    message: "username is required to confirmResetPassword"
  },
  [AuthValidationErrorCode.EmptyConfirmSignUpCode]: {
    message: "code is required to confirmSignUp"
  },
  [AuthValidationErrorCode.EmptyConfirmSignUpUsername]: {
    message: "username is required to confirmSignUp"
  },
  [AuthValidationErrorCode.EmptyConfirmResetPasswordConfirmationCode]: {
    message: "confirmationCode is required to confirmResetPassword"
  },
  [AuthValidationErrorCode.EmptyConfirmResetPasswordNewPassword]: {
    message: "newPassword is required to confirmResetPassword"
  },
  [AuthValidationErrorCode.EmptyResendSignUpCodeUsername]: {
    message: "username is required to confirmSignUp"
  },
  [AuthValidationErrorCode.EmptyResetPasswordUsername]: {
    message: "username is required to resetPassword"
  },
  [AuthValidationErrorCode.EmptySignInPassword]: {
    message: "password is required to signIn"
  },
  [AuthValidationErrorCode.EmptySignInUsername]: {
    message: "username is required to signIn"
  },
  [AuthValidationErrorCode.EmptySignUpPassword]: {
    message: "password is required to signUp"
  },
  [AuthValidationErrorCode.EmptySignUpUsername]: {
    message: "username is required to signUp"
  },
  [AuthValidationErrorCode.CustomAuthSignInPassword]: {
    message: "A password is not needed when signing in with CUSTOM_WITHOUT_SRP",
    recoverySuggestion: "Do not include a password in your signIn call."
  },
  [AuthValidationErrorCode.IncorrectMFAMethod]: {
    message: "Incorrect MFA method was chosen. It should be either SMS, TOTP, or EMAIL",
    recoverySuggestion: "Try to pass SMS, TOTP, or EMAIL as the challengeResponse"
  },
  [AuthValidationErrorCode.EmptyVerifyTOTPSetupCode]: {
    message: "code is required to verifyTotpSetup"
  },
  [AuthValidationErrorCode.EmptyUpdatePassword]: {
    message: "oldPassword and newPassword are required to changePassword"
  },
  [AuthValidationErrorCode.EmptyConfirmUserAttributeCode]: {
    message: "confirmation code is required to confirmUserAttribute"
  },
  [AuthValidationErrorCode.InvalidPreferredChallenge]: {
    message: "The preferred challenge is not enabled in your backend configuration",
    recoverySuggestion: "Ensure the authentication method is enabled in your Amplify backend configuration"
  }
};
var AuthErrorStrings;
(function(AuthErrorStrings2) {
  AuthErrorStrings2["DEFAULT_MSG"] = "Authentication Error";
  AuthErrorStrings2["EMPTY_EMAIL"] = "Email cannot be empty";
  AuthErrorStrings2["EMPTY_PHONE"] = "Phone number cannot be empty";
  AuthErrorStrings2["EMPTY_USERNAME"] = "Username cannot be empty";
  AuthErrorStrings2["INVALID_USERNAME"] = "The username should either be a string or one of the sign in types";
  AuthErrorStrings2["EMPTY_PASSWORD"] = "Password cannot be empty";
  AuthErrorStrings2["EMPTY_CODE"] = "Confirmation code cannot be empty";
  AuthErrorStrings2["SIGN_UP_ERROR"] = "Error creating account";
  AuthErrorStrings2["NO_MFA"] = "No valid MFA method provided";
  AuthErrorStrings2["INVALID_MFA"] = "Invalid MFA type";
  AuthErrorStrings2["EMPTY_CHALLENGE"] = "Challenge response cannot be empty";
  AuthErrorStrings2["NO_USER_SESSION"] = "Failed to get the session because the user is empty";
  AuthErrorStrings2["NETWORK_ERROR"] = "Network Error";
  AuthErrorStrings2["DEVICE_CONFIG"] = "Device tracking has not been configured in this User Pool";
  AuthErrorStrings2["AUTOSIGNIN_ERROR"] = "Please use your credentials to sign in";
  AuthErrorStrings2["OAUTH_ERROR"] = "Couldn't finish OAuth flow, check your User Pool HostedUI settings";
})(AuthErrorStrings || (AuthErrorStrings = {}));
var AuthErrorCodes;
(function(AuthErrorCodes2) {
  AuthErrorCodes2["SignInException"] = "SignInException";
  AuthErrorCodes2["OAuthSignInError"] = "OAuthSignInException";
})(AuthErrorCodes || (AuthErrorCodes = {}));

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/errors/AuthError.mjs
var AuthError = class _AuthError extends AmplifyError {
  constructor(params) {
    super(params);
    this.constructor = _AuthError;
    Object.setPrototypeOf(this, _AuthError.prototype);
  }
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/errors/utils/assertValidationError.mjs
function assertValidationError(assertion, name2) {
  const { message, recoverySuggestion } = validationErrorMap[name2];
  if (!assertion) {
    throw new AuthError({ name: name2, message, recoverySuggestion });
  }
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/parsers/regionParsers.mjs
function getRegionFromUserPoolId(userPoolId) {
  const region = userPoolId == null ? void 0 : userPoolId.split("_")[0];
  if (!userPoolId || userPoolId.indexOf("_") < 0 || !region || typeof region !== "string")
    throw new AuthError({
      name: "InvalidUserPoolId",
      message: "Invalid user pool id provided."
    });
  return region;
}
function getRegionFromIdentityPoolId(identityPoolId) {
  if (!identityPoolId || !identityPoolId.includes(":")) {
    throw new AuthError({
      name: "InvalidIdentityPoolIdException",
      message: "Invalid identity pool id provided.",
      recoverySuggestion: "Make sure a valid identityPoolId is given in the config."
    });
  }
  return identityPoolId.split(":")[0];
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/types/errors.mjs
var AssociateSoftwareTokenException;
(function(AssociateSoftwareTokenException2) {
  AssociateSoftwareTokenException2["ConcurrentModificationException"] = "ConcurrentModificationException";
  AssociateSoftwareTokenException2["ForbiddenException"] = "ForbiddenException";
  AssociateSoftwareTokenException2["InternalErrorException"] = "InternalErrorException";
  AssociateSoftwareTokenException2["InvalidParameterException"] = "InvalidParameterException";
  AssociateSoftwareTokenException2["NotAuthorizedException"] = "NotAuthorizedException";
  AssociateSoftwareTokenException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  AssociateSoftwareTokenException2["SoftwareTokenMFANotFoundException"] = "SoftwareTokenMFANotFoundException";
})(AssociateSoftwareTokenException || (AssociateSoftwareTokenException = {}));
var ChangePasswordException;
(function(ChangePasswordException2) {
  ChangePasswordException2["ForbiddenException"] = "ForbiddenException";
  ChangePasswordException2["InternalErrorException"] = "InternalErrorException";
  ChangePasswordException2["InvalidParameterException"] = "InvalidParameterException";
  ChangePasswordException2["InvalidPasswordException"] = "InvalidPasswordException";
  ChangePasswordException2["LimitExceededException"] = "LimitExceededException";
  ChangePasswordException2["NotAuthorizedException"] = "NotAuthorizedException";
  ChangePasswordException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  ChangePasswordException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  ChangePasswordException2["TooManyRequestsException"] = "TooManyRequestsException";
  ChangePasswordException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  ChangePasswordException2["UserNotFoundException"] = "UserNotFoundException";
})(ChangePasswordException || (ChangePasswordException = {}));
var ConfirmDeviceException;
(function(ConfirmDeviceException2) {
  ConfirmDeviceException2["ForbiddenException"] = "ForbiddenException";
  ConfirmDeviceException2["InternalErrorException"] = "InternalErrorException";
  ConfirmDeviceException2["InvalidLambdaResponseException"] = "InvalidLambdaResponseException";
  ConfirmDeviceException2["InvalidParameterException"] = "InvalidParameterException";
  ConfirmDeviceException2["InvalidPasswordException"] = "InvalidPasswordException";
  ConfirmDeviceException2["InvalidUserPoolConfigurationException"] = "InvalidUserPoolConfigurationException";
  ConfirmDeviceException2["NotAuthorizedException"] = "NotAuthorizedException";
  ConfirmDeviceException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  ConfirmDeviceException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  ConfirmDeviceException2["TooManyRequestsException"] = "TooManyRequestsException";
  ConfirmDeviceException2["UsernameExistsException"] = "UsernameExistsException";
  ConfirmDeviceException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  ConfirmDeviceException2["UserNotFoundException"] = "UserNotFoundException";
})(ConfirmDeviceException || (ConfirmDeviceException = {}));
var ConfirmForgotPasswordException;
(function(ConfirmForgotPasswordException2) {
  ConfirmForgotPasswordException2["CodeMismatchException"] = "CodeMismatchException";
  ConfirmForgotPasswordException2["ExpiredCodeException"] = "ExpiredCodeException";
  ConfirmForgotPasswordException2["ForbiddenException"] = "ForbiddenException";
  ConfirmForgotPasswordException2["InternalErrorException"] = "InternalErrorException";
  ConfirmForgotPasswordException2["InvalidLambdaResponseException"] = "InvalidLambdaResponseException";
  ConfirmForgotPasswordException2["InvalidParameterException"] = "InvalidParameterException";
  ConfirmForgotPasswordException2["InvalidPasswordException"] = "InvalidPasswordException";
  ConfirmForgotPasswordException2["LimitExceededException"] = "LimitExceededException";
  ConfirmForgotPasswordException2["NotAuthorizedException"] = "NotAuthorizedException";
  ConfirmForgotPasswordException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  ConfirmForgotPasswordException2["TooManyFailedAttemptsException"] = "TooManyFailedAttemptsException";
  ConfirmForgotPasswordException2["TooManyRequestsException"] = "TooManyRequestsException";
  ConfirmForgotPasswordException2["UnexpectedLambdaException"] = "UnexpectedLambdaException";
  ConfirmForgotPasswordException2["UserLambdaValidationException"] = "UserLambdaValidationException";
  ConfirmForgotPasswordException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  ConfirmForgotPasswordException2["UserNotFoundException"] = "UserNotFoundException";
})(ConfirmForgotPasswordException || (ConfirmForgotPasswordException = {}));
var ConfirmSignUpException;
(function(ConfirmSignUpException2) {
  ConfirmSignUpException2["AliasExistsException"] = "AliasExistsException";
  ConfirmSignUpException2["CodeMismatchException"] = "CodeMismatchException";
  ConfirmSignUpException2["ExpiredCodeException"] = "ExpiredCodeException";
  ConfirmSignUpException2["ForbiddenException"] = "ForbiddenException";
  ConfirmSignUpException2["InternalErrorException"] = "InternalErrorException";
  ConfirmSignUpException2["InvalidLambdaResponseException"] = "InvalidLambdaResponseException";
  ConfirmSignUpException2["InvalidParameterException"] = "InvalidParameterException";
  ConfirmSignUpException2["LimitExceededException"] = "LimitExceededException";
  ConfirmSignUpException2["NotAuthorizedException"] = "NotAuthorizedException";
  ConfirmSignUpException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  ConfirmSignUpException2["TooManyFailedAttemptsException"] = "TooManyFailedAttemptsException";
  ConfirmSignUpException2["TooManyRequestsException"] = "TooManyRequestsException";
  ConfirmSignUpException2["UnexpectedLambdaException"] = "UnexpectedLambdaException";
  ConfirmSignUpException2["UserLambdaValidationException"] = "UserLambdaValidationException";
  ConfirmSignUpException2["UserNotFoundException"] = "UserNotFoundException";
})(ConfirmSignUpException || (ConfirmSignUpException = {}));
var DeleteUserAttributesException;
(function(DeleteUserAttributesException2) {
  DeleteUserAttributesException2["ForbiddenException"] = "ForbiddenException";
  DeleteUserAttributesException2["InternalErrorException"] = "InternalErrorException";
  DeleteUserAttributesException2["InvalidParameterException"] = "InvalidParameterException";
  DeleteUserAttributesException2["NotAuthorizedException"] = "NotAuthorizedException";
  DeleteUserAttributesException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  DeleteUserAttributesException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  DeleteUserAttributesException2["TooManyRequestsException"] = "TooManyRequestsException";
  DeleteUserAttributesException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  DeleteUserAttributesException2["UserNotFoundException"] = "UserNotFoundException";
})(DeleteUserAttributesException || (DeleteUserAttributesException = {}));
var DeleteUserException;
(function(DeleteUserException2) {
  DeleteUserException2["ForbiddenException"] = "ForbiddenException";
  DeleteUserException2["InternalErrorException"] = "InternalErrorException";
  DeleteUserException2["InvalidParameterException"] = "InvalidParameterException";
  DeleteUserException2["NotAuthorizedException"] = "NotAuthorizedException";
  DeleteUserException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  DeleteUserException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  DeleteUserException2["TooManyRequestsException"] = "TooManyRequestsException";
  DeleteUserException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  DeleteUserException2["UserNotFoundException"] = "UserNotFoundException";
})(DeleteUserException || (DeleteUserException = {}));
var ForgetDeviceException;
(function(ForgetDeviceException2) {
  ForgetDeviceException2["ForbiddenException"] = "ForbiddenException";
  ForgetDeviceException2["InternalErrorException"] = "InternalErrorException";
  ForgetDeviceException2["InvalidParameterException"] = "InvalidParameterException";
  ForgetDeviceException2["InvalidUserPoolConfigurationException"] = "InvalidUserPoolConfigurationException";
  ForgetDeviceException2["NotAuthorizedException"] = "NotAuthorizedException";
  ForgetDeviceException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  ForgetDeviceException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  ForgetDeviceException2["TooManyRequestsException"] = "TooManyRequestsException";
  ForgetDeviceException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  ForgetDeviceException2["UserNotFoundException"] = "UserNotFoundException";
})(ForgetDeviceException || (ForgetDeviceException = {}));
var ForgotPasswordException;
(function(ForgotPasswordException2) {
  ForgotPasswordException2["CodeDeliveryFailureException"] = "CodeDeliveryFailureException";
  ForgotPasswordException2["ForbiddenException"] = "ForbiddenException";
  ForgotPasswordException2["InternalErrorException"] = "InternalErrorException";
  ForgotPasswordException2["InvalidEmailRoleAccessPolicyException"] = "InvalidEmailRoleAccessPolicyException";
  ForgotPasswordException2["InvalidLambdaResponseException"] = "InvalidLambdaResponseException";
  ForgotPasswordException2["InvalidParameterException"] = "InvalidParameterException";
  ForgotPasswordException2["InvalidSmsRoleAccessPolicyException"] = "InvalidSmsRoleAccessPolicyException";
  ForgotPasswordException2["InvalidSmsRoleTrustRelationshipException"] = "InvalidSmsRoleTrustRelationshipException";
  ForgotPasswordException2["LimitExceededException"] = "LimitExceededException";
  ForgotPasswordException2["NotAuthorizedException"] = "NotAuthorizedException";
  ForgotPasswordException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  ForgotPasswordException2["TooManyRequestsException"] = "TooManyRequestsException";
  ForgotPasswordException2["UnexpectedLambdaException"] = "UnexpectedLambdaException";
  ForgotPasswordException2["UserLambdaValidationException"] = "UserLambdaValidationException";
  ForgotPasswordException2["UserNotFoundException"] = "UserNotFoundException";
})(ForgotPasswordException || (ForgotPasswordException = {}));
var GetUserException;
(function(GetUserException2) {
  GetUserException2["ForbiddenException"] = "ForbiddenException";
  GetUserException2["InternalErrorException"] = "InternalErrorException";
  GetUserException2["InvalidParameterException"] = "InvalidParameterException";
  GetUserException2["NotAuthorizedException"] = "NotAuthorizedException";
  GetUserException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  GetUserException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  GetUserException2["TooManyRequestsException"] = "TooManyRequestsException";
  GetUserException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  GetUserException2["UserNotFoundException"] = "UserNotFoundException";
})(GetUserException || (GetUserException = {}));
var GetIdException;
(function(GetIdException2) {
  GetIdException2["ExternalServiceException"] = "ExternalServiceException";
  GetIdException2["InternalErrorException"] = "InternalErrorException";
  GetIdException2["InvalidParameterException"] = "InvalidParameterException";
  GetIdException2["LimitExceededException"] = "LimitExceededException";
  GetIdException2["NotAuthorizedException"] = "NotAuthorizedException";
  GetIdException2["ResourceConflictException"] = "ResourceConflictException";
  GetIdException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  GetIdException2["TooManyRequestsException"] = "TooManyRequestsException";
})(GetIdException || (GetIdException = {}));
var GetCredentialsForIdentityException;
(function(GetCredentialsForIdentityException2) {
  GetCredentialsForIdentityException2["ExternalServiceException"] = "ExternalServiceException";
  GetCredentialsForIdentityException2["InternalErrorException"] = "InternalErrorException";
  GetCredentialsForIdentityException2["InvalidIdentityPoolConfigurationException"] = "InvalidIdentityPoolConfigurationException";
  GetCredentialsForIdentityException2["InvalidParameterException"] = "InvalidParameterException";
  GetCredentialsForIdentityException2["NotAuthorizedException"] = "NotAuthorizedException";
  GetCredentialsForIdentityException2["ResourceConflictException"] = "ResourceConflictException";
  GetCredentialsForIdentityException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  GetCredentialsForIdentityException2["TooManyRequestsException"] = "TooManyRequestsException";
})(GetCredentialsForIdentityException || (GetCredentialsForIdentityException = {}));
var GetUserAttributeVerificationException;
(function(GetUserAttributeVerificationException2) {
  GetUserAttributeVerificationException2["CodeDeliveryFailureException"] = "CodeDeliveryFailureException";
  GetUserAttributeVerificationException2["ForbiddenException"] = "ForbiddenException";
  GetUserAttributeVerificationException2["InternalErrorException"] = "InternalErrorException";
  GetUserAttributeVerificationException2["InvalidEmailRoleAccessPolicyException"] = "InvalidEmailRoleAccessPolicyException";
  GetUserAttributeVerificationException2["InvalidLambdaResponseException"] = "InvalidLambdaResponseException";
  GetUserAttributeVerificationException2["InvalidParameterException"] = "InvalidParameterException";
  GetUserAttributeVerificationException2["InvalidSmsRoleAccessPolicyException"] = "InvalidSmsRoleAccessPolicyException";
  GetUserAttributeVerificationException2["InvalidSmsRoleTrustRelationshipException"] = "InvalidSmsRoleTrustRelationshipException";
  GetUserAttributeVerificationException2["LimitExceededException"] = "LimitExceededException";
  GetUserAttributeVerificationException2["NotAuthorizedException"] = "NotAuthorizedException";
  GetUserAttributeVerificationException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  GetUserAttributeVerificationException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  GetUserAttributeVerificationException2["TooManyRequestsException"] = "TooManyRequestsException";
  GetUserAttributeVerificationException2["UnexpectedLambdaException"] = "UnexpectedLambdaException";
  GetUserAttributeVerificationException2["UserLambdaValidationException"] = "UserLambdaValidationException";
  GetUserAttributeVerificationException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  GetUserAttributeVerificationException2["UserNotFoundException"] = "UserNotFoundException";
})(GetUserAttributeVerificationException || (GetUserAttributeVerificationException = {}));
var GlobalSignOutException;
(function(GlobalSignOutException2) {
  GlobalSignOutException2["ForbiddenException"] = "ForbiddenException";
  GlobalSignOutException2["InternalErrorException"] = "InternalErrorException";
  GlobalSignOutException2["InvalidParameterException"] = "InvalidParameterException";
  GlobalSignOutException2["NotAuthorizedException"] = "NotAuthorizedException";
  GlobalSignOutException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  GlobalSignOutException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  GlobalSignOutException2["TooManyRequestsException"] = "TooManyRequestsException";
  GlobalSignOutException2["UserNotConfirmedException"] = "UserNotConfirmedException";
})(GlobalSignOutException || (GlobalSignOutException = {}));
var InitiateAuthException;
(function(InitiateAuthException2) {
  InitiateAuthException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  InitiateAuthException2["ForbiddenException"] = "ForbiddenException";
  InitiateAuthException2["InternalErrorException"] = "InternalErrorException";
  InitiateAuthException2["InvalidLambdaResponseException"] = "InvalidLambdaResponseException";
  InitiateAuthException2["InvalidParameterException"] = "InvalidParameterException";
  InitiateAuthException2["InvalidSmsRoleAccessPolicyException"] = "InvalidSmsRoleAccessPolicyException";
  InitiateAuthException2["InvalidSmsRoleTrustRelationshipException"] = "InvalidSmsRoleTrustRelationshipException";
  InitiateAuthException2["InvalidUserPoolConfigurationException"] = "InvalidUserPoolConfigurationException";
  InitiateAuthException2["NotAuthorizedException"] = "NotAuthorizedException";
  InitiateAuthException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  InitiateAuthException2["TooManyRequestsException"] = "TooManyRequestsException";
  InitiateAuthException2["UnexpectedLambdaException"] = "UnexpectedLambdaException";
  InitiateAuthException2["UserLambdaValidationException"] = "UserLambdaValidationException";
  InitiateAuthException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  InitiateAuthException2["UserNotFoundException"] = "UserNotFoundException";
})(InitiateAuthException || (InitiateAuthException = {}));
var ResendConfirmationException;
(function(ResendConfirmationException2) {
  ResendConfirmationException2["CodeDeliveryFailureException"] = "CodeDeliveryFailureException";
  ResendConfirmationException2["ForbiddenException"] = "ForbiddenException";
  ResendConfirmationException2["InternalErrorException"] = "InternalErrorException";
  ResendConfirmationException2["InvalidEmailRoleAccessPolicyException"] = "InvalidEmailRoleAccessPolicyException";
  ResendConfirmationException2["InvalidLambdaResponseException"] = "InvalidLambdaResponseException";
  ResendConfirmationException2["InvalidParameterException"] = "InvalidParameterException";
  ResendConfirmationException2["InvalidSmsRoleAccessPolicyException"] = "InvalidSmsRoleAccessPolicyException";
  ResendConfirmationException2["InvalidSmsRoleTrustRelationshipException"] = "InvalidSmsRoleTrustRelationshipException";
  ResendConfirmationException2["LimitExceededException"] = "LimitExceededException";
  ResendConfirmationException2["NotAuthorizedException"] = "NotAuthorizedException";
  ResendConfirmationException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  ResendConfirmationException2["TooManyRequestsException"] = "TooManyRequestsException";
  ResendConfirmationException2["UnexpectedLambdaException"] = "UnexpectedLambdaException";
  ResendConfirmationException2["UserLambdaValidationException"] = "UserLambdaValidationException";
  ResendConfirmationException2["UserNotFoundException"] = "UserNotFoundException";
})(ResendConfirmationException || (ResendConfirmationException = {}));
var RespondToAuthChallengeException;
(function(RespondToAuthChallengeException2) {
  RespondToAuthChallengeException2["AliasExistsException"] = "AliasExistsException";
  RespondToAuthChallengeException2["CodeMismatchException"] = "CodeMismatchException";
  RespondToAuthChallengeException2["ExpiredCodeException"] = "ExpiredCodeException";
  RespondToAuthChallengeException2["ForbiddenException"] = "ForbiddenException";
  RespondToAuthChallengeException2["InternalErrorException"] = "InternalErrorException";
  RespondToAuthChallengeException2["InvalidLambdaResponseException"] = "InvalidLambdaResponseException";
  RespondToAuthChallengeException2["InvalidParameterException"] = "InvalidParameterException";
  RespondToAuthChallengeException2["InvalidPasswordException"] = "InvalidPasswordException";
  RespondToAuthChallengeException2["InvalidSmsRoleAccessPolicyException"] = "InvalidSmsRoleAccessPolicyException";
  RespondToAuthChallengeException2["InvalidSmsRoleTrustRelationshipException"] = "InvalidSmsRoleTrustRelationshipException";
  RespondToAuthChallengeException2["InvalidUserPoolConfigurationException"] = "InvalidUserPoolConfigurationException";
  RespondToAuthChallengeException2["MFAMethodNotFoundException"] = "MFAMethodNotFoundException";
  RespondToAuthChallengeException2["NotAuthorizedException"] = "NotAuthorizedException";
  RespondToAuthChallengeException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  RespondToAuthChallengeException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  RespondToAuthChallengeException2["SoftwareTokenMFANotFoundException"] = "SoftwareTokenMFANotFoundException";
  RespondToAuthChallengeException2["TooManyRequestsException"] = "TooManyRequestsException";
  RespondToAuthChallengeException2["UnexpectedLambdaException"] = "UnexpectedLambdaException";
  RespondToAuthChallengeException2["UserLambdaValidationException"] = "UserLambdaValidationException";
  RespondToAuthChallengeException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  RespondToAuthChallengeException2["UserNotFoundException"] = "UserNotFoundException";
})(RespondToAuthChallengeException || (RespondToAuthChallengeException = {}));
var SetUserMFAPreferenceException;
(function(SetUserMFAPreferenceException2) {
  SetUserMFAPreferenceException2["ForbiddenException"] = "ForbiddenException";
  SetUserMFAPreferenceException2["InternalErrorException"] = "InternalErrorException";
  SetUserMFAPreferenceException2["InvalidParameterException"] = "InvalidParameterException";
  SetUserMFAPreferenceException2["NotAuthorizedException"] = "NotAuthorizedException";
  SetUserMFAPreferenceException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  SetUserMFAPreferenceException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  SetUserMFAPreferenceException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  SetUserMFAPreferenceException2["UserNotFoundException"] = "UserNotFoundException";
})(SetUserMFAPreferenceException || (SetUserMFAPreferenceException = {}));
var SignUpException;
(function(SignUpException2) {
  SignUpException2["CodeDeliveryFailureException"] = "CodeDeliveryFailureException";
  SignUpException2["InternalErrorException"] = "InternalErrorException";
  SignUpException2["InvalidEmailRoleAccessPolicyException"] = "InvalidEmailRoleAccessPolicyException";
  SignUpException2["InvalidLambdaResponseException"] = "InvalidLambdaResponseException";
  SignUpException2["InvalidParameterException"] = "InvalidParameterException";
  SignUpException2["InvalidPasswordException"] = "InvalidPasswordException";
  SignUpException2["InvalidSmsRoleAccessPolicyException"] = "InvalidSmsRoleAccessPolicyException";
  SignUpException2["InvalidSmsRoleTrustRelationshipException"] = "InvalidSmsRoleTrustRelationshipException";
  SignUpException2["NotAuthorizedException"] = "NotAuthorizedException";
  SignUpException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  SignUpException2["TooManyRequestsException"] = "TooManyRequestsException";
  SignUpException2["UnexpectedLambdaException"] = "UnexpectedLambdaException";
  SignUpException2["UserLambdaValidationException"] = "UserLambdaValidationException";
  SignUpException2["UsernameExistsException"] = "UsernameExistsException";
})(SignUpException || (SignUpException = {}));
var UpdateUserAttributesException;
(function(UpdateUserAttributesException2) {
  UpdateUserAttributesException2["AliasExistsException"] = "AliasExistsException";
  UpdateUserAttributesException2["CodeDeliveryFailureException"] = "CodeDeliveryFailureException";
  UpdateUserAttributesException2["CodeMismatchException"] = "CodeMismatchException";
  UpdateUserAttributesException2["ExpiredCodeException"] = "ExpiredCodeException";
  UpdateUserAttributesException2["ForbiddenException"] = "ForbiddenException";
  UpdateUserAttributesException2["InternalErrorException"] = "InternalErrorException";
  UpdateUserAttributesException2["InvalidEmailRoleAccessPolicyException"] = "InvalidEmailRoleAccessPolicyException";
  UpdateUserAttributesException2["InvalidLambdaResponseException"] = "InvalidLambdaResponseException";
  UpdateUserAttributesException2["InvalidParameterException"] = "InvalidParameterException";
  UpdateUserAttributesException2["InvalidSmsRoleAccessPolicyException"] = "InvalidSmsRoleAccessPolicyException";
  UpdateUserAttributesException2["InvalidSmsRoleTrustRelationshipException"] = "InvalidSmsRoleTrustRelationshipException";
  UpdateUserAttributesException2["NotAuthorizedException"] = "NotAuthorizedException";
  UpdateUserAttributesException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  UpdateUserAttributesException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  UpdateUserAttributesException2["TooManyRequestsException"] = "TooManyRequestsException";
  UpdateUserAttributesException2["UnexpectedLambdaException"] = "UnexpectedLambdaException";
  UpdateUserAttributesException2["UserLambdaValidationException"] = "UserLambdaValidationException";
  UpdateUserAttributesException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  UpdateUserAttributesException2["UserNotFoundException"] = "UserNotFoundException";
})(UpdateUserAttributesException || (UpdateUserAttributesException = {}));
var VerifySoftwareTokenException;
(function(VerifySoftwareTokenException2) {
  VerifySoftwareTokenException2["CodeMismatchException"] = "CodeMismatchException";
  VerifySoftwareTokenException2["EnableSoftwareTokenMFAException"] = "EnableSoftwareTokenMFAException";
  VerifySoftwareTokenException2["ForbiddenException"] = "ForbiddenException";
  VerifySoftwareTokenException2["InternalErrorException"] = "InternalErrorException";
  VerifySoftwareTokenException2["InvalidParameterException"] = "InvalidParameterException";
  VerifySoftwareTokenException2["InvalidUserPoolConfigurationException"] = "InvalidUserPoolConfigurationException";
  VerifySoftwareTokenException2["NotAuthorizedException"] = "NotAuthorizedException";
  VerifySoftwareTokenException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  VerifySoftwareTokenException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  VerifySoftwareTokenException2["SoftwareTokenMFANotFoundException"] = "SoftwareTokenMFANotFoundException";
  VerifySoftwareTokenException2["TooManyRequestsException"] = "TooManyRequestsException";
  VerifySoftwareTokenException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  VerifySoftwareTokenException2["UserNotFoundException"] = "UserNotFoundException";
})(VerifySoftwareTokenException || (VerifySoftwareTokenException = {}));
var VerifyUserAttributeException;
(function(VerifyUserAttributeException2) {
  VerifyUserAttributeException2["AliasExistsException"] = "AliasExistsException";
  VerifyUserAttributeException2["CodeMismatchException"] = "CodeMismatchException";
  VerifyUserAttributeException2["ExpiredCodeException"] = "ExpiredCodeException";
  VerifyUserAttributeException2["ForbiddenException"] = "ForbiddenException";
  VerifyUserAttributeException2["InternalErrorException"] = "InternalErrorException";
  VerifyUserAttributeException2["InvalidParameterException"] = "InvalidParameterException";
  VerifyUserAttributeException2["LimitExceededException"] = "LimitExceededException";
  VerifyUserAttributeException2["NotAuthorizedException"] = "NotAuthorizedException";
  VerifyUserAttributeException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  VerifyUserAttributeException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  VerifyUserAttributeException2["TooManyRequestsException"] = "TooManyRequestsException";
  VerifyUserAttributeException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  VerifyUserAttributeException2["UserNotFoundException"] = "UserNotFoundException";
})(VerifyUserAttributeException || (VerifyUserAttributeException = {}));
var UpdateDeviceStatusException;
(function(UpdateDeviceStatusException2) {
  UpdateDeviceStatusException2["ForbiddenException"] = "ForbiddenException";
  UpdateDeviceStatusException2["InternalErrorException"] = "InternalErrorException";
  UpdateDeviceStatusException2["InvalidParameterException"] = "InvalidParameterException";
  UpdateDeviceStatusException2["InvalidUserPoolConfigurationException"] = "InvalidUserPoolConfigurationException";
  UpdateDeviceStatusException2["NotAuthorizedException"] = "NotAuthorizedException";
  UpdateDeviceStatusException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  UpdateDeviceStatusException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  UpdateDeviceStatusException2["TooManyRequestsException"] = "TooManyRequestsException";
  UpdateDeviceStatusException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  UpdateDeviceStatusException2["UserNotFoundException"] = "UserNotFoundException";
})(UpdateDeviceStatusException || (UpdateDeviceStatusException = {}));
var ListDevicesException;
(function(ListDevicesException2) {
  ListDevicesException2["ForbiddenException"] = "ForbiddenException";
  ListDevicesException2["InternalErrorException"] = "InternalErrorException";
  ListDevicesException2["InvalidParameterException"] = "InvalidParameterException";
  ListDevicesException2["InvalidUserPoolConfigurationException"] = "InvalidUserPoolConfigurationException";
  ListDevicesException2["NotAuthorizedException"] = "NotAuthorizedException";
  ListDevicesException2["PasswordResetRequiredException"] = "PasswordResetRequiredException";
  ListDevicesException2["ResourceNotFoundException"] = "ResourceNotFoundException";
  ListDevicesException2["TooManyRequestsException"] = "TooManyRequestsException";
  ListDevicesException2["UserNotConfirmedException"] = "UserNotConfirmedException";
  ListDevicesException2["UserNotFoundException"] = "UserNotFoundException";
})(ListDevicesException || (ListDevicesException = {}));

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/errors/constants.mjs
var USER_UNAUTHENTICATED_EXCEPTION = "UserUnAuthenticatedException";
var USER_ALREADY_AUTHENTICATED_EXCEPTION = "UserAlreadyAuthenticatedException";
var DEVICE_METADATA_NOT_FOUND_EXCEPTION = "DeviceMetadataNotFoundException";
var AUTO_SIGN_IN_EXCEPTION = "AutoSignInException";
var INVALID_REDIRECT_EXCEPTION = "InvalidRedirectException";
var INVALID_APP_SCHEME_EXCEPTION = "InvalidAppSchemeException";
var INVALID_PREFERRED_REDIRECT_EXCEPTION = "InvalidPreferredRedirectUrlException";
var invalidRedirectException = new AuthError({
  name: INVALID_REDIRECT_EXCEPTION,
  message: "signInRedirect or signOutRedirect had an invalid format or was not found.",
  recoverySuggestion: "Please make sure the signIn/Out redirect in your oauth config is valid."
});
var invalidAppSchemeException = new AuthError({
  name: INVALID_APP_SCHEME_EXCEPTION,
  message: "A valid non-http app scheme was not found in the config.",
  recoverySuggestion: "Please make sure a valid custom app scheme is present in the config."
});
var invalidPreferredRedirectUrlException = new AuthError({
  name: INVALID_PREFERRED_REDIRECT_EXCEPTION,
  message: "The given preferredRedirectUrl does not match any items in the redirectSignOutUrls array from the config.",
  recoverySuggestion: "Please make sure a matching preferredRedirectUrl is provided."
});
var INVALID_ORIGIN_EXCEPTION = "InvalidOriginException";
var invalidOriginException = new AuthError({
  name: INVALID_ORIGIN_EXCEPTION,
  message: "redirect is coming from a different origin. The oauth flow needs to be initiated from the same origin",
  recoverySuggestion: "Please call signInWithRedirect from the same origin."
});
var TOKEN_REFRESH_EXCEPTION = "TokenRefreshException";
var UNEXPECTED_SIGN_IN_INTERRUPTION_EXCEPTION = "UnexpectedSignInInterruptionException";

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/types.mjs
function assertAuthTokens(tokens) {
  if (!tokens || !tokens.accessToken) {
    throw new AuthError({
      name: USER_UNAUTHENTICATED_EXCEPTION,
      message: "User needs to be authenticated to call this API.",
      recoverySuggestion: "Sign in before calling this API again."
    });
  }
}
function assertIdTokenInAuthTokens(tokens) {
  if (!tokens || !tokens.idToken) {
    throw new AuthError({
      name: USER_UNAUTHENTICATED_EXCEPTION,
      message: "User needs to be authenticated to call this API.",
      recoverySuggestion: "Sign in before calling this API again."
    });
  }
}
var oAuthTokenRefreshException = new AuthError({
  name: TOKEN_REFRESH_EXCEPTION,
  message: `Token refresh is not supported when authenticated with the 'implicit grant' (token) oauth flow. 
	Please change your oauth configuration to use 'code grant' flow.`,
  recoverySuggestion: `Please logout and change your Amplify configuration to use "code grant" flow. 
	E.g { responseType: 'code' }`
});
var tokenRefreshException = new AuthError({
  name: USER_UNAUTHENTICATED_EXCEPTION,
  message: "User needs to be authenticated to call this API.",
  recoverySuggestion: "Sign in before calling this API again."
});
function assertAuthTokensWithRefreshToken(tokens) {
  if (isAuthenticatedWithImplicitOauthFlow(tokens)) {
    throw oAuthTokenRefreshException;
  }
  if (!isAuthenticatedWithRefreshToken(tokens)) {
    throw tokenRefreshException;
  }
}
function assertDeviceMetadata(deviceMetadata) {
  if (!deviceMetadata || !deviceMetadata.deviceKey || !deviceMetadata.deviceGroupKey || !deviceMetadata.randomPassword) {
    throw new AuthError({
      name: DEVICE_METADATA_NOT_FOUND_EXCEPTION,
      message: "Either deviceKey, deviceGroupKey or secretPassword were not found during the sign-in process.",
      recoverySuggestion: "Make sure to not clear storage after calling the signIn API."
    });
  }
}
var OAuthStorageKeys = {
  inflightOAuth: "inflightOAuth",
  oauthSignIn: "oauthSignIn",
  oauthPKCE: "oauthPKCE",
  oauthState: "oauthState"
};
function isAuthenticated(tokens) {
  return (tokens == null ? void 0 : tokens.accessToken) || (tokens == null ? void 0 : tokens.idToken);
}
function isAuthenticatedWithRefreshToken(tokens) {
  return isAuthenticated(tokens) && (tokens == null ? void 0 : tokens.refreshToken);
}
function isAuthenticatedWithImplicitOauthFlow(tokens) {
  return isAuthenticated(tokens) && !(tokens == null ? void 0 : tokens.refreshToken);
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/apis/internal/getCurrentUser.mjs
var getCurrentUser = async (amplify) => {
  var _a, _b;
  const authConfig = (_a = amplify.getConfig().Auth) == null ? void 0 : _a.Cognito;
  assertTokenProviderConfig(authConfig);
  const tokens = await amplify.Auth.getTokens({ forceRefresh: false });
  assertAuthTokens(tokens);
  const { "cognito:username": username, sub } = ((_b = tokens.idToken) == null ? void 0 : _b.payload) ?? {};
  const authUser = {
    username,
    userId: sub
  };
  const signInDetails = getSignInDetailsFromTokens(tokens);
  if (signInDetails) {
    authUser.signInDetails = signInDetails;
  }
  return authUser;
};
function getSignInDetailsFromTokens(tokens) {
  return tokens == null ? void 0 : tokens.signInDetails;
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/apis/getCurrentUser.mjs
var getCurrentUser2 = async () => {
  return getCurrentUser(Amplify);
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/utils/getAuthUserAgentValue.mjs
var getAuthUserAgentValue = (action, customUserAgentDetails) => getAmplifyUserAgent({
  category: Category.Auth,
  action,
  ...customUserAgentDetails
});

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/factories/serviceClients/cognitoIdentityProvider/shared/serde/createUserPoolSerializer.mjs
var createUserPoolSerializer = (operation) => (input, endpoint) => {
  const headers = getSharedHeaders(operation);
  const body = JSON.stringify(input);
  return buildHttpRpcRequest(endpoint, headers, body);
};
var getSharedHeaders = (operation) => ({
  "content-type": "application/x-amz-json-1.1",
  "x-amz-target": `AWSCognitoIdentityProviderService.${operation}`
});
var buildHttpRpcRequest = ({ url }, headers, body) => ({
  headers,
  url,
  body,
  method: "POST"
});

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/errors/utils/assertServiceError.mjs
function assertServiceError(error) {
  if (!error || error.name === "Error" || error instanceof TypeError) {
    throw new AuthError({
      name: AmplifyErrorCode.Unknown,
      message: "An unknown error has occurred.",
      underlyingError: error
    });
  }
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/factories/serviceClients/cognitoIdentityProvider/shared/serde/createUserPoolDeserializer.mjs
var createUserPoolDeserializer = () => async (response) => {
  if (response.statusCode >= 300) {
    const error = await parseJsonError(response);
    assertServiceError(error);
    throw new AuthError({
      name: error.name,
      message: error.message,
      metadata: error.$metadata
    });
  }
  return parseJsonBody(response);
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/factories/serviceClients/cognitoIdentityProvider/shared/handler/cognitoUserPoolTransferHandler.mjs
var disableCacheMiddlewareFactory = () => (next, _) => async function disableCacheMiddleware(request) {
  request.headers["cache-control"] = "no-store";
  return next(request);
};
var cognitoUserPoolTransferHandler = composeTransferHandler(unauthenticatedHandler, [disableCacheMiddlewareFactory]);

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/constants.mjs
var COGNITO_IDP_SERVICE_NAME = "cognito-idp";

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/factories/serviceClients/cognitoIdentityProvider/constants.mjs
var DEFAULT_SERVICE_CLIENT_API_CONFIG = {
  service: COGNITO_IDP_SERVICE_NAME,
  retryDecider: getRetryDecider(parseJsonError),
  computeDelay: jitteredBackoff,
  get userAgentValue() {
    return getAmplifyUserAgent();
  },
  cache: "no-store"
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/factories/serviceClients/cognitoIdentityProvider/createInitiateAuthClient.mjs
var createInitiateAuthClient = (config) => composeServiceApi(cognitoUserPoolTransferHandler, createUserPoolSerializer("InitiateAuth"), createUserPoolDeserializer(), {
  ...DEFAULT_SERVICE_CLIENT_API_CONFIG,
  ...config
});

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/factories/serviceClients/cognitoIdentityProvider/createRespondToAuthChallengeClient.mjs
var createRespondToAuthChallengeClient = (config) => composeServiceApi(cognitoUserPoolTransferHandler, createUserPoolSerializer("RespondToAuthChallenge"), createUserPoolDeserializer(), {
  ...DEFAULT_SERVICE_CLIENT_API_CONFIG,
  ...config
});

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/factories/serviceClients/cognitoIdentityProvider/createAssociateSoftwareTokenClient.mjs
var createAssociateSoftwareTokenClient = (config) => composeServiceApi(cognitoUserPoolTransferHandler, createUserPoolSerializer("AssociateSoftwareToken"), createUserPoolDeserializer(), {
  ...DEFAULT_SERVICE_CLIENT_API_CONFIG,
  ...config
});

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/cognitoUserPoolEndpointResolver.mjs
var cognitoUserPoolEndpointResolver = ({ region }) => ({
  url: new AmplifyUrl(`https://${COGNITO_IDP_SERVICE_NAME}.${region}.${getDnsSuffix(region)}`)
});

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/factories/createCognitoUserPoolEndpointResolver.mjs
var createCognitoUserPoolEndpointResolver = ({ endpointOverride }) => (input) => {
  if (endpointOverride) {
    return { url: new AmplifyUrl(endpointOverride) };
  }
  return cognitoUserPoolEndpointResolver(input);
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/factories/serviceClients/cognitoIdentityProvider/createGetTokensFromRefreshTokenClient.mjs
var createGetTokensFromRefreshTokenClient = (config) => composeServiceApi(cognitoUserPoolTransferHandler, createUserPoolSerializer("GetTokensFromRefreshToken"), createUserPoolDeserializer(), {
  ...DEFAULT_SERVICE_CLIENT_API_CONFIG,
  ...config
});

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/refreshAuthTokens.mjs
var refreshAuthTokensFunction = async ({ tokens, authConfig, username, clientMetadata }) => {
  var _a;
  assertTokenProviderConfig(authConfig == null ? void 0 : authConfig.Cognito);
  const { userPoolId, userPoolClientId, userPoolEndpoint } = authConfig.Cognito;
  const region = getRegionFromUserPoolId(userPoolId);
  assertAuthTokensWithRefreshToken(tokens);
  const getTokensFromRefreshToken = createGetTokensFromRefreshTokenClient({
    endpointResolver: createCognitoUserPoolEndpointResolver({
      endpointOverride: userPoolEndpoint
    })
  });
  const { AuthenticationResult } = await getTokensFromRefreshToken({ region }, {
    ClientId: userPoolClientId,
    RefreshToken: tokens.refreshToken,
    DeviceKey: (_a = tokens.deviceMetadata) == null ? void 0 : _a.deviceKey,
    ClientMetadata: clientMetadata
  });
  const accessToken = decodeJWT((AuthenticationResult == null ? void 0 : AuthenticationResult.AccessToken) ?? "");
  const idToken = (AuthenticationResult == null ? void 0 : AuthenticationResult.IdToken) ? decodeJWT(AuthenticationResult.IdToken) : void 0;
  const { iat } = accessToken.payload;
  if (!iat) {
    throw new AuthError({
      name: "iatNotFoundException",
      message: "iat not found in access token"
    });
  }
  const clockDrift = iat * 1e3 - (/* @__PURE__ */ new Date()).getTime();
  return {
    accessToken,
    idToken,
    clockDrift,
    refreshToken: (AuthenticationResult == null ? void 0 : AuthenticationResult.RefreshToken) ?? tokens.refreshToken,
    username
  };
};
var refreshAuthTokens = deDupeAsyncFunction(refreshAuthTokensFunction);

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/tokenProvider/types.mjs
var AuthTokenStorageKeys = {
  accessToken: "accessToken",
  idToken: "idToken",
  oidcProvider: "oidcProvider",
  clockDrift: "clockDrift",
  refreshToken: "refreshToken",
  deviceKey: "deviceKey",
  randomPasswordKey: "randomPasswordKey",
  deviceGroupKey: "deviceGroupKey",
  signInDetails: "signInDetails",
  oauthMetadata: "oauthMetadata"
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/tokenProvider/errorHelpers.mjs
var TokenProviderErrorCode;
(function(TokenProviderErrorCode2) {
  TokenProviderErrorCode2["InvalidAuthTokens"] = "InvalidAuthTokens";
})(TokenProviderErrorCode || (TokenProviderErrorCode = {}));
var tokenValidationErrorMap = {
  [TokenProviderErrorCode.InvalidAuthTokens]: {
    message: "Invalid tokens.",
    recoverySuggestion: "Make sure the tokens are valid."
  }
};
var assert = createAssertionFunction(tokenValidationErrorMap);

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/tokenProvider/constants.mjs
var AUTH_KEY_PREFIX = "CognitoIdentityServiceProvider";

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/tokenProvider/TokenStore.mjs
var DefaultTokenStore = class {
  getKeyValueStorage() {
    if (!this.keyValueStorage) {
      throw new AuthError({
        name: "KeyValueStorageNotFoundException",
        message: "KeyValueStorage was not found in TokenStore"
      });
    }
    return this.keyValueStorage;
  }
  setKeyValueStorage(keyValueStorage) {
    this.keyValueStorage = keyValueStorage;
  }
  setAuthConfig(authConfig) {
    this.authConfig = authConfig;
  }
  async loadTokens() {
    try {
      const authKeys = await this.getAuthKeys();
      const accessTokenString = await this.getKeyValueStorage().getItem(authKeys.accessToken);
      if (!accessTokenString) {
        throw new AuthError({
          name: "NoSessionFoundException",
          message: "Auth session was not found. Make sure to call signIn."
        });
      }
      const accessToken = decodeJWT(accessTokenString);
      const itString = await this.getKeyValueStorage().getItem(authKeys.idToken);
      const idToken = itString ? decodeJWT(itString) : void 0;
      const refreshToken = await this.getKeyValueStorage().getItem(authKeys.refreshToken) ?? void 0;
      const clockDriftString = await this.getKeyValueStorage().getItem(authKeys.clockDrift) ?? "0";
      const clockDrift = Number.parseInt(clockDriftString);
      const signInDetails = await this.getKeyValueStorage().getItem(authKeys.signInDetails);
      const tokens = {
        accessToken,
        idToken,
        refreshToken,
        deviceMetadata: await this.getDeviceMetadata() ?? void 0,
        clockDrift,
        username: await this.getLastAuthUser()
      };
      if (signInDetails) {
        tokens.signInDetails = JSON.parse(signInDetails);
      }
      return tokens;
    } catch (err) {
      return null;
    }
  }
  async storeTokens(tokens) {
    assert(tokens !== void 0, TokenProviderErrorCode.InvalidAuthTokens);
    const lastAuthUser = tokens.username;
    await this.getKeyValueStorage().setItem(this.getLastAuthUserKey(), lastAuthUser);
    const authKeys = await this.getAuthKeys();
    await this.getKeyValueStorage().setItem(authKeys.accessToken, tokens.accessToken.toString());
    if (tokens.idToken) {
      await this.getKeyValueStorage().setItem(authKeys.idToken, tokens.idToken.toString());
    } else {
      await this.getKeyValueStorage().removeItem(authKeys.idToken);
    }
    if (tokens.refreshToken) {
      await this.getKeyValueStorage().setItem(authKeys.refreshToken, tokens.refreshToken);
    } else {
      await this.getKeyValueStorage().removeItem(authKeys.refreshToken);
    }
    if (tokens.deviceMetadata) {
      if (tokens.deviceMetadata.deviceKey) {
        await this.getKeyValueStorage().setItem(authKeys.deviceKey, tokens.deviceMetadata.deviceKey);
      }
      if (tokens.deviceMetadata.deviceGroupKey) {
        await this.getKeyValueStorage().setItem(authKeys.deviceGroupKey, tokens.deviceMetadata.deviceGroupKey);
      }
      await this.getKeyValueStorage().setItem(authKeys.randomPasswordKey, tokens.deviceMetadata.randomPassword);
    }
    if (tokens.signInDetails) {
      await this.getKeyValueStorage().setItem(authKeys.signInDetails, JSON.stringify(tokens.signInDetails));
    } else {
      await this.getKeyValueStorage().removeItem(authKeys.signInDetails);
    }
    await this.getKeyValueStorage().setItem(authKeys.clockDrift, `${tokens.clockDrift}`);
  }
  async clearTokens() {
    const authKeys = await this.getAuthKeys();
    await Promise.all([
      this.getKeyValueStorage().removeItem(authKeys.accessToken),
      this.getKeyValueStorage().removeItem(authKeys.idToken),
      this.getKeyValueStorage().removeItem(authKeys.clockDrift),
      this.getKeyValueStorage().removeItem(authKeys.refreshToken),
      this.getKeyValueStorage().removeItem(authKeys.signInDetails),
      this.getKeyValueStorage().removeItem(this.getLastAuthUserKey()),
      this.getKeyValueStorage().removeItem(authKeys.oauthMetadata)
    ]);
  }
  async getDeviceMetadata(username) {
    const authKeys = await this.getAuthKeys(username);
    const deviceKey = await this.getKeyValueStorage().getItem(authKeys.deviceKey);
    const deviceGroupKey = await this.getKeyValueStorage().getItem(authKeys.deviceGroupKey);
    const randomPassword = await this.getKeyValueStorage().getItem(authKeys.randomPasswordKey);
    return randomPassword && deviceGroupKey && deviceKey ? {
      deviceKey,
      deviceGroupKey,
      randomPassword
    } : null;
  }
  async clearDeviceMetadata(username) {
    const authKeys = await this.getAuthKeys(username);
    await Promise.all([
      this.getKeyValueStorage().removeItem(authKeys.deviceKey),
      this.getKeyValueStorage().removeItem(authKeys.deviceGroupKey),
      this.getKeyValueStorage().removeItem(authKeys.randomPasswordKey)
    ]);
  }
  async getAuthKeys(username) {
    var _a;
    assertTokenProviderConfig((_a = this.authConfig) == null ? void 0 : _a.Cognito);
    const lastAuthUser = username ?? await this.getLastAuthUser();
    return createKeysForAuthStorage(AUTH_KEY_PREFIX, `${this.authConfig.Cognito.userPoolClientId}.${lastAuthUser}`);
  }
  getLastAuthUserKey() {
    var _a;
    assertTokenProviderConfig((_a = this.authConfig) == null ? void 0 : _a.Cognito);
    const identifier = this.authConfig.Cognito.userPoolClientId;
    return `${AUTH_KEY_PREFIX}.${identifier}.LastAuthUser`;
  }
  async getLastAuthUser() {
    const lastAuthUser = await this.getKeyValueStorage().getItem(this.getLastAuthUserKey()) ?? "username";
    return lastAuthUser;
  }
  async setOAuthMetadata(metadata) {
    const { oauthMetadata: oauthMetadataKey } = await this.getAuthKeys();
    await this.getKeyValueStorage().setItem(oauthMetadataKey, JSON.stringify(metadata));
  }
  async getOAuthMetadata() {
    const { oauthMetadata: oauthMetadataKey } = await this.getAuthKeys();
    const oauthMetadata = await this.getKeyValueStorage().getItem(oauthMetadataKey);
    return oauthMetadata && JSON.parse(oauthMetadata);
  }
};
var createKeysForAuthStorage = (provider, identifier) => {
  return getAuthStorageKeys(AuthTokenStorageKeys)(`${provider}`, identifier);
};
function getAuthStorageKeys(authKeys) {
  const keys = Object.values({ ...authKeys });
  return (prefix, identifier) => keys.reduce((acc, authKey) => ({
    ...acc,
    [authKey]: `${prefix}.${identifier}.${authKey}`
  }), {});
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/signInWithRedirectStore.mjs
var V5_HOSTED_UI_KEY = "amplify-signin-with-hostedUI";
var name = "CognitoIdentityServiceProvider";
var DefaultOAuthStore = class {
  constructor(keyValueStorage) {
    this.keyValueStorage = keyValueStorage;
  }
  async clearOAuthInflightData() {
    assertTokenProviderConfig(this.cognitoConfig);
    const authKeys = createKeysForAuthStorage2(name, this.cognitoConfig.userPoolClientId);
    await Promise.all([
      this.keyValueStorage.removeItem(authKeys.inflightOAuth),
      this.keyValueStorage.removeItem(authKeys.oauthPKCE),
      this.keyValueStorage.removeItem(authKeys.oauthState)
    ]);
  }
  async clearOAuthData() {
    assertTokenProviderConfig(this.cognitoConfig);
    const authKeys = createKeysForAuthStorage2(name, this.cognitoConfig.userPoolClientId);
    await this.clearOAuthInflightData();
    await this.keyValueStorage.removeItem(V5_HOSTED_UI_KEY);
    return this.keyValueStorage.removeItem(authKeys.oauthSignIn);
  }
  loadOAuthState() {
    assertTokenProviderConfig(this.cognitoConfig);
    const authKeys = createKeysForAuthStorage2(name, this.cognitoConfig.userPoolClientId);
    return this.keyValueStorage.getItem(authKeys.oauthState);
  }
  storeOAuthState(state) {
    assertTokenProviderConfig(this.cognitoConfig);
    const authKeys = createKeysForAuthStorage2(name, this.cognitoConfig.userPoolClientId);
    return this.keyValueStorage.setItem(authKeys.oauthState, state);
  }
  loadPKCE() {
    assertTokenProviderConfig(this.cognitoConfig);
    const authKeys = createKeysForAuthStorage2(name, this.cognitoConfig.userPoolClientId);
    return this.keyValueStorage.getItem(authKeys.oauthPKCE);
  }
  storePKCE(pkce) {
    assertTokenProviderConfig(this.cognitoConfig);
    const authKeys = createKeysForAuthStorage2(name, this.cognitoConfig.userPoolClientId);
    return this.keyValueStorage.setItem(authKeys.oauthPKCE, pkce);
  }
  setAuthConfig(authConfigParam) {
    this.cognitoConfig = authConfigParam;
  }
  async loadOAuthInFlight() {
    assertTokenProviderConfig(this.cognitoConfig);
    const authKeys = createKeysForAuthStorage2(name, this.cognitoConfig.userPoolClientId);
    return await this.keyValueStorage.getItem(authKeys.inflightOAuth) === "true";
  }
  async storeOAuthInFlight(inflight) {
    assertTokenProviderConfig(this.cognitoConfig);
    const authKeys = createKeysForAuthStorage2(name, this.cognitoConfig.userPoolClientId);
    await this.keyValueStorage.setItem(authKeys.inflightOAuth, `${inflight}`);
  }
  async loadOAuthSignIn() {
    var _a;
    assertTokenProviderConfig(this.cognitoConfig);
    const authKeys = createKeysForAuthStorage2(name, this.cognitoConfig.userPoolClientId);
    const isLegacyHostedUISignIn = await this.keyValueStorage.getItem(V5_HOSTED_UI_KEY);
    const [isOAuthSignIn, preferPrivateSession] = ((_a = await this.keyValueStorage.getItem(authKeys.oauthSignIn)) == null ? void 0 : _a.split(",")) ?? [];
    return {
      isOAuthSignIn: isOAuthSignIn === "true" || isLegacyHostedUISignIn === "true",
      preferPrivateSession: preferPrivateSession === "true"
    };
  }
  async storeOAuthSignIn(oauthSignIn, preferPrivateSession = false) {
    assertTokenProviderConfig(this.cognitoConfig);
    const authKeys = createKeysForAuthStorage2(name, this.cognitoConfig.userPoolClientId);
    await this.keyValueStorage.setItem(authKeys.oauthSignIn, `${oauthSignIn},${preferPrivateSession}`);
  }
};
var createKeysForAuthStorage2 = (provider, identifier) => {
  return getAuthStorageKeys(OAuthStorageKeys)(provider, identifier);
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/oauth/oAuthStore.mjs
var oAuthStore = new DefaultOAuthStore(defaultStorage);

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/oauth/inflightPromise.mjs
var inflightPromises = [];
var addInflightPromise = (resolver) => {
  inflightPromises.push(resolver);
};
var resolveAndClearInflightPromises = () => {
  var _a;
  while (inflightPromises.length) {
    (_a = inflightPromises.pop()) == null ? void 0 : _a();
  }
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/tokenProvider/TokenOrchestrator.mjs
var TokenOrchestrator = class {
  constructor() {
    this.waitForInflightOAuth = isBrowser() ? async () => {
      if (!await oAuthStore.loadOAuthInFlight()) {
        return;
      }
      if (this.inflightPromise) {
        return this.inflightPromise;
      }
      this.inflightPromise = new Promise((resolve, _reject) => {
        addInflightPromise(resolve);
      });
      return this.inflightPromise;
    } : async () => {
    };
  }
  setAuthConfig(authConfig) {
    oAuthStore.setAuthConfig(authConfig.Cognito);
    this.authConfig = authConfig;
  }
  setTokenRefresher(tokenRefresher) {
    this.tokenRefresher = tokenRefresher;
  }
  setAuthTokenStore(tokenStore) {
    this.tokenStore = tokenStore;
  }
  getTokenStore() {
    if (!this.tokenStore) {
      throw new AuthError({
        name: "EmptyTokenStoreException",
        message: "TokenStore not set"
      });
    }
    return this.tokenStore;
  }
  getTokenRefresher() {
    if (!this.tokenRefresher) {
      throw new AuthError({
        name: "EmptyTokenRefresherException",
        message: "TokenRefresher not set"
      });
    }
    return this.tokenRefresher;
  }
  setClientMetadataProvider(clientMetadataProvider) {
    this.clientMetadataProvider = clientMetadataProvider;
  }
  async getTokens(options) {
    var _a, _b, _c, _d, _e, _f;
    let tokens;
    try {
      assertTokenProviderConfig((_a = this.authConfig) == null ? void 0 : _a.Cognito);
    } catch (_err) {
      return null;
    }
    await this.waitForInflightOAuth();
    this.inflightPromise = void 0;
    tokens = await this.getTokenStore().loadTokens();
    const username = await this.getTokenStore().getLastAuthUser();
    if (tokens === null) {
      return null;
    }
    const idTokenExpired = !!(tokens == null ? void 0 : tokens.idToken) && isTokenExpired({
      expiresAt: (((_c = (_b = tokens.idToken) == null ? void 0 : _b.payload) == null ? void 0 : _c.exp) ?? 0) * 1e3,
      clockDrift: tokens.clockDrift ?? 0
    });
    const accessTokenExpired = isTokenExpired({
      expiresAt: (((_e = (_d = tokens.accessToken) == null ? void 0 : _d.payload) == null ? void 0 : _e.exp) ?? 0) * 1e3,
      clockDrift: tokens.clockDrift ?? 0
    });
    if ((options == null ? void 0 : options.forceRefresh) || idTokenExpired || accessTokenExpired) {
      tokens = await this.refreshTokens({
        tokens,
        username,
        clientMetadata: (options == null ? void 0 : options.clientMetadata) ?? await ((_f = this.clientMetadataProvider) == null ? void 0 : _f.call(this))
      });
      if (tokens === null) {
        return null;
      }
    }
    return {
      accessToken: tokens == null ? void 0 : tokens.accessToken,
      idToken: tokens == null ? void 0 : tokens.idToken,
      signInDetails: tokens == null ? void 0 : tokens.signInDetails
    };
  }
  async refreshTokens({ tokens, username, clientMetadata }) {
    try {
      const { signInDetails } = tokens;
      const newTokens = await this.getTokenRefresher()({
        tokens,
        authConfig: this.authConfig,
        username,
        clientMetadata
      });
      newTokens.signInDetails = signInDetails;
      await this.setTokens({ tokens: newTokens });
      Hub.dispatch("auth", { event: "tokenRefresh" }, "Auth", AMPLIFY_SYMBOL);
      return newTokens;
    } catch (err) {
      return this.handleErrors(err);
    }
  }
  handleErrors(err) {
    assertServiceError(err);
    const shouldClearTokens = this.isAuthenticationError(err);
    if (shouldClearTokens) {
      this.clearTokens();
    }
    Hub.dispatch("auth", {
      event: "tokenRefresh_failure",
      data: { error: err }
    }, "Auth", AMPLIFY_SYMBOL);
    if (err.name.startsWith("NotAuthorizedException")) {
      return null;
    }
    throw err;
  }
  isAuthenticationError(err) {
    const authErrorNames = [
      "NotAuthorizedException",
      // Refresh token is expired or invalid
      "TokenRevokedException",
      // Token was revoked by admin
      "UserNotFoundException",
      // User no longer exists
      "PasswordResetRequiredException",
      // User must reset password
      "UserNotConfirmedException",
      // User account is not confirmed
      "RefreshTokenReuseException"
      // Refresh token invalidated by rotation
    ];
    return authErrorNames.some((errorName) => {
      var _a, _b;
      return (_b = (_a = err == null ? void 0 : err.name) == null ? void 0 : _a.startsWith) == null ? void 0 : _b.call(_a, errorName);
    });
  }
  async setTokens({ tokens }) {
    return this.getTokenStore().storeTokens(tokens);
  }
  async clearTokens() {
    return this.getTokenStore().clearTokens();
  }
  getDeviceMetadata(username) {
    return this.getTokenStore().getDeviceMetadata(username);
  }
  clearDeviceMetadata(username) {
    return this.getTokenStore().clearDeviceMetadata(username);
  }
  setOAuthMetadata(metadata) {
    return this.getTokenStore().setOAuthMetadata(metadata);
  }
  getOAuthMetadata() {
    return this.getTokenStore().getOAuthMetadata();
  }
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/tokenProvider/CognitoUserPoolsTokenProvider.mjs
var CognitoUserPoolsTokenProvider = class {
  constructor() {
    this.authTokenStore = new DefaultTokenStore();
    this.authTokenStore.setKeyValueStorage(defaultStorage);
    this.tokenOrchestrator = new TokenOrchestrator();
    this.tokenOrchestrator.setAuthTokenStore(this.authTokenStore);
    this.tokenOrchestrator.setTokenRefresher(refreshAuthTokens);
  }
  getTokens(options = {}) {
    return this.tokenOrchestrator.getTokens(options);
  }
  setKeyValueStorage(keyValueStorage) {
    this.authTokenStore.setKeyValueStorage(keyValueStorage);
  }
  setClientMetadataProvider(clientMetadataProvider) {
    this.tokenOrchestrator.setClientMetadataProvider(clientMetadataProvider);
  }
  setAuthConfig(authConfig) {
    this.authTokenStore.setAuthConfig(authConfig);
    this.tokenOrchestrator.setAuthConfig(authConfig);
  }
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/tokenProvider/tokenProvider.mjs
var cognitoUserPoolsTokenProvider = new CognitoUserPoolsTokenProvider();
var { tokenOrchestrator } = cognitoUserPoolsTokenProvider;

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/tokenProvider/cacheTokens.mjs
async function cacheCognitoTokens(AuthenticationResult) {
  if (AuthenticationResult.AccessToken) {
    const accessToken = decodeJWT(AuthenticationResult.AccessToken);
    const accessTokenIssuedAtInMillis = (accessToken.payload.iat || 0) * 1e3;
    const currentTime = (/* @__PURE__ */ new Date()).getTime();
    const clockDrift = accessTokenIssuedAtInMillis > 0 ? accessTokenIssuedAtInMillis - currentTime : 0;
    let idToken;
    let refreshToken;
    let deviceMetadata;
    if (AuthenticationResult.RefreshToken) {
      refreshToken = AuthenticationResult.RefreshToken;
    }
    if (AuthenticationResult.IdToken) {
      idToken = decodeJWT(AuthenticationResult.IdToken);
    }
    if (AuthenticationResult == null ? void 0 : AuthenticationResult.NewDeviceMetadata) {
      deviceMetadata = AuthenticationResult.NewDeviceMetadata;
    }
    const tokens = {
      accessToken,
      idToken,
      refreshToken,
      clockDrift,
      deviceMetadata,
      username: AuthenticationResult.username
    };
    if (AuthenticationResult == null ? void 0 : AuthenticationResult.signInDetails) {
      tokens.signInDetails = AuthenticationResult.signInDetails;
    }
    await tokenOrchestrator.setTokens({
      tokens
    });
  } else {
    throw new AmplifyError({
      message: "Invalid tokens",
      name: "InvalidTokens",
      recoverySuggestion: "Check Cognito UserPool settings"
    });
  }
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/dispatchSignedInHubEvent.mjs
var ERROR_MESSAGE = "Unable to get user session following successful sign-in.";
var dispatchSignedInHubEvent = async () => {
  try {
    Hub.dispatch("auth", {
      event: "signedIn",
      data: await getCurrentUser2()
    }, "Auth", AMPLIFY_SYMBOL);
  } catch (error) {
    if (error.name === USER_UNAUTHENTICATED_EXCEPTION) {
      throw new AuthError({
        name: UNEXPECTED_SIGN_IN_INTERRUPTION_EXCEPTION,
        message: ERROR_MESSAGE,
        recoverySuggestion: "This most likely is due to auth tokens not being persisted. If you are using cookie store, please ensure cookies can be correctly set from your server."
      });
    }
    throw error;
  }
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/client/utils/store/autoSignInStore.mjs
function defaultState() {
  return {
    active: false
  };
}
var autoSignInReducer = (state, action) => {
  switch (action.type) {
    case "SET_USERNAME":
      return {
        ...state,
        username: action.value
      };
    case "SET_SESSION":
      return {
        ...state,
        session: action.value
      };
    case "START":
      return {
        ...state,
        active: true
      };
    case "RESET":
      return defaultState();
    default:
      return state;
  }
};
var createAutoSignInStore = (reducer) => {
  let currentState = reducer(defaultState(), { type: "RESET" });
  return {
    getState: () => currentState,
    dispatch: (action) => {
      currentState = reducer(currentState, action);
    }
  };
};
var autoSignInStore = createAutoSignInStore(autoSignInReducer);

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/client/utils/store/signInStore.mjs
var MS_TO_EXPIRY = 3 * 60 * 1e3;
var TGT_STATE = "CognitoSignInState";
var SIGN_IN_STATE_KEYS = {
  username: `${TGT_STATE}.username`,
  challengeName: `${TGT_STATE}.challengeName`,
  signInSession: `${TGT_STATE}.signInSession`,
  expiry: `${TGT_STATE}.expiry`
};
var signInReducer = (state, action) => {
  switch (action.type) {
    case "SET_SIGN_IN_SESSION":
      persistSignInState({ signInSession: action.value });
      return {
        ...state,
        signInSession: action.value
      };
    case "SET_SIGN_IN_STATE":
      persistSignInState(action.value);
      return {
        ...action.value
      };
    case "SET_CHALLENGE_NAME":
      persistSignInState({ challengeName: action.value });
      return {
        ...state,
        challengeName: action.value
      };
    case "SET_USERNAME":
      persistSignInState({ username: action.value });
      return {
        ...state,
        username: action.value
      };
    case "SET_INITIAL_STATE":
      return getInitialState();
    case "RESET_STATE":
      clearPersistedSignInState();
      return getDefaultState();
    default:
      return state;
  }
};
var isExpired = (expiryDate) => {
  const expiryTimestamp = Number(expiryDate);
  const currentTimestamp = Date.now();
  return expiryTimestamp <= currentTimestamp;
};
var resetActiveSignInState = () => {
  signInStore.dispatch({ type: "RESET_STATE" });
};
var clearPersistedSignInState = () => {
  for (const stateKey of Object.values(SIGN_IN_STATE_KEYS)) {
    syncSessionStorage.removeItem(stateKey);
  }
};
var getDefaultState = () => ({
  username: void 0,
  challengeName: void 0,
  signInSession: void 0
});
var getInitialState = () => {
  const expiry = syncSessionStorage.getItem(SIGN_IN_STATE_KEYS.expiry);
  if (!expiry || isExpired(expiry)) {
    clearPersistedSignInState();
    return getDefaultState();
  }
  const username = syncSessionStorage.getItem(SIGN_IN_STATE_KEYS.username) ?? void 0;
  const challengeName = syncSessionStorage.getItem(SIGN_IN_STATE_KEYS.challengeName) ?? void 0;
  const signInSession = syncSessionStorage.getItem(SIGN_IN_STATE_KEYS.signInSession) ?? void 0;
  return {
    username,
    challengeName,
    signInSession
  };
};
var createStore = (reducer) => {
  let currentState = reducer(getDefaultState(), { type: "SET_INITIAL_STATE" });
  return {
    getState: () => currentState,
    dispatch: (action) => {
      currentState = reducer(currentState, action);
    }
  };
};
var signInStore = createStore(signInReducer);
function setActiveSignInState(state) {
  signInStore.dispatch({
    type: "SET_SIGN_IN_STATE",
    value: state
  });
}
var persistSignInState = ({ challengeName, signInSession, username }) => {
  username && syncSessionStorage.setItem(SIGN_IN_STATE_KEYS.username, username);
  challengeName && syncSessionStorage.setItem(SIGN_IN_STATE_KEYS.challengeName, challengeName);
  if (signInSession) {
    syncSessionStorage.setItem(SIGN_IN_STATE_KEYS.signInSession, signInSession);
    syncSessionStorage.setItem(SIGN_IN_STATE_KEYS.expiry, String(Date.now() + MS_TO_EXPIRY));
  }
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/client/utils/passkey/errors/passkeyErrorPlatformConstants.mjs
var NOT_SUPPORTED_RECOVERY_SUGGESTION = "Passkeys may not be supported on this device. Ensure your application is running in a secure context (HTTPS) and Web Authentication API is supported.";

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/client/utils/passkey/errors/passkeyError.mjs
var PasskeyError = class _PasskeyError extends AmplifyError {
  constructor(params) {
    super(params);
    this.constructor = _PasskeyError;
    Object.setPrototypeOf(this, _PasskeyError.prototype);
  }
};
var PasskeyErrorCode;
(function(PasskeyErrorCode2) {
  PasskeyErrorCode2["PasskeyNotSupported"] = "PasskeyNotSupported";
  PasskeyErrorCode2["PasskeyAlreadyExists"] = "PasskeyAlreadyExists";
  PasskeyErrorCode2["InvalidPasskeyRegistrationOptions"] = "InvalidPasskeyRegistrationOptions";
  PasskeyErrorCode2["InvalidPasskeyAuthenticationOptions"] = "InvalidPasskeyAuthenticationOptions";
  PasskeyErrorCode2["RelyingPartyMismatch"] = "RelyingPartyMismatch";
  PasskeyErrorCode2["PasskeyRegistrationFailed"] = "PasskeyRegistrationFailed";
  PasskeyErrorCode2["PasskeyRetrievalFailed"] = "PasskeyRetrievalFailed";
  PasskeyErrorCode2["PasskeyRegistrationCanceled"] = "PasskeyRegistrationCanceled";
  PasskeyErrorCode2["PasskeyAuthenticationCanceled"] = "PasskeyAuthenticationCanceled";
  PasskeyErrorCode2["PasskeyOperationAborted"] = "PasskeyOperationAborted";
})(PasskeyErrorCode || (PasskeyErrorCode = {}));
var ABORT_OR_CANCEL_RECOVERY_SUGGESTION = "User may have canceled the ceremony or another interruption has occurred. Check underlying error for details.";
var MISCONFIGURATION_RECOVERY_SUGGESTION = "Ensure your user pool is configured to support the WEB_AUTHN as an authentication factor.";
var passkeyErrorMap = {
  [PasskeyErrorCode.PasskeyNotSupported]: {
    message: "Passkeys may not be supported on this device.",
    recoverySuggestion: NOT_SUPPORTED_RECOVERY_SUGGESTION
  },
  [PasskeyErrorCode.InvalidPasskeyRegistrationOptions]: {
    message: "Invalid passkey registration options.",
    recoverySuggestion: MISCONFIGURATION_RECOVERY_SUGGESTION
  },
  [PasskeyErrorCode.InvalidPasskeyAuthenticationOptions]: {
    message: "Invalid passkey authentication options.",
    recoverySuggestion: MISCONFIGURATION_RECOVERY_SUGGESTION
  },
  [PasskeyErrorCode.PasskeyRegistrationFailed]: {
    message: "Device failed to create passkey.",
    recoverySuggestion: NOT_SUPPORTED_RECOVERY_SUGGESTION
  },
  [PasskeyErrorCode.PasskeyRetrievalFailed]: {
    message: "Device failed to retrieve passkey.",
    recoverySuggestion: "Passkeys may not be available on this device. Try an alternative authentication factor like PASSWORD, EMAIL_OTP, or SMS_OTP."
  },
  [PasskeyErrorCode.PasskeyAlreadyExists]: {
    message: "Passkey already exists in authenticator.",
    recoverySuggestion: "Proceed with existing passkey or try again after deleting the credential."
  },
  [PasskeyErrorCode.PasskeyRegistrationCanceled]: {
    message: "Passkey registration ceremony has been canceled.",
    recoverySuggestion: ABORT_OR_CANCEL_RECOVERY_SUGGESTION
  },
  [PasskeyErrorCode.PasskeyAuthenticationCanceled]: {
    message: "Passkey authentication ceremony has been canceled.",
    recoverySuggestion: ABORT_OR_CANCEL_RECOVERY_SUGGESTION
  },
  [PasskeyErrorCode.PasskeyOperationAborted]: {
    message: "Passkey operation has been aborted.",
    recoverySuggestion: ABORT_OR_CANCEL_RECOVERY_SUGGESTION
  },
  [PasskeyErrorCode.RelyingPartyMismatch]: {
    message: "Relying party does not match current domain.",
    recoverySuggestion: "Ensure relying party identifier matches current domain."
  }
};
var assertPasskeyError = createAssertionFunction(passkeyErrorMap, PasskeyError);

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/client/utils/passkey/errors/handlePasskeyError.mjs
var handlePasskeyError = (err) => {
  if (err instanceof Error) {
    if (err.name === "AbortError") {
      const { message, recoverySuggestion } = passkeyErrorMap[PasskeyErrorCode.PasskeyOperationAborted];
      return new PasskeyError({
        name: PasskeyErrorCode.PasskeyOperationAborted,
        message,
        recoverySuggestion,
        underlyingError: err
      });
    }
    if (err.name === "SecurityError") {
      const { message, recoverySuggestion } = passkeyErrorMap[PasskeyErrorCode.RelyingPartyMismatch];
      return new PasskeyError({
        name: PasskeyErrorCode.RelyingPartyMismatch,
        message,
        recoverySuggestion,
        underlyingError: err
      });
    }
  }
  return new PasskeyError({
    name: AmplifyErrorCode.Unknown,
    message: "An unknown error has occurred.",
    underlyingError: err
  });
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/client/utils/passkey/errors/handlePasskeyAuthenticationError.mjs
var handlePasskeyAuthenticationError = (err) => {
  if (err instanceof PasskeyError) {
    return err;
  }
  if (err instanceof Error) {
    if (err.name === "NotAllowedError") {
      const { message, recoverySuggestion } = passkeyErrorMap[PasskeyErrorCode.PasskeyAuthenticationCanceled];
      return new PasskeyError({
        name: PasskeyErrorCode.PasskeyAuthenticationCanceled,
        message,
        recoverySuggestion,
        underlyingError: err
      });
    }
  }
  return handlePasskeyError(err);
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/client/utils/passkey/getIsPasskeySupported.mjs
var getIsPasskeySupported = () => {
  return isBrowser() && window.isSecureContext && "credentials" in navigator && typeof window.PublicKeyCredential === "function";
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/convert/base64url/convertArrayBufferToBase64Url.mjs
var convertArrayBufferToBase64Url = (buffer) => {
  return base64Encoder.convert(new Uint8Array(buffer), {
    urlSafe: true,
    skipPadding: true
  });
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/convert/base64url/convertBase64UrlToArrayBuffer.mjs
var convertBase64UrlToArrayBuffer = (base64url) => {
  return Uint8Array.from(base64Decoder.convert(base64url, { urlSafe: true }), (x) => x.charCodeAt(0)).buffer;
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/client/utils/passkey/serde.mjs
var deserializeJsonToPkcGetOptions = (input) => {
  const challengeBuffer = convertBase64UrlToArrayBuffer(input.challenge);
  const allowedCredentialsWithBuffer = (input.allowCredentials || []).map((allowedCred) => ({
    ...allowedCred,
    id: convertBase64UrlToArrayBuffer(allowedCred.id)
  }));
  return {
    ...input,
    challenge: challengeBuffer,
    allowCredentials: allowedCredentialsWithBuffer
  };
};
var serializePkcWithAssertionToJson = (input) => {
  const response = {
    clientDataJSON: convertArrayBufferToBase64Url(input.response.clientDataJSON),
    authenticatorData: convertArrayBufferToBase64Url(input.response.authenticatorData),
    signature: convertArrayBufferToBase64Url(input.response.signature)
  };
  if (input.response.userHandle) {
    response.userHandle = convertArrayBufferToBase64Url(input.response.userHandle);
  }
  const resultJson = {
    id: input.id,
    rawId: convertArrayBufferToBase64Url(input.rawId),
    type: input.type,
    clientExtensionResults: input.getClientExtensionResults(),
    response
  };
  if (input.authenticatorAttachment) {
    resultJson.authenticatorAttachment = input.authenticatorAttachment;
  }
  return resultJson;
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/client/utils/passkey/types/index.mjs
function assertCredentialIsPkcWithAuthenticatorAssertionResponse(credential) {
  assertPasskeyError(credential && credential instanceof PublicKeyCredential && credential.response instanceof AuthenticatorAssertionResponse, PasskeyErrorCode.PasskeyRetrievalFailed);
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/client/utils/passkey/getPasskey.mjs
var getPasskey = async (input) => {
  try {
    const isPasskeySupported = getIsPasskeySupported();
    assertPasskeyError(isPasskeySupported, PasskeyErrorCode.PasskeyNotSupported);
    const passkeyGetOptions = deserializeJsonToPkcGetOptions(input);
    const credential = await navigator.credentials.get({
      publicKey: passkeyGetOptions
    });
    assertCredentialIsPkcWithAuthenticatorAssertionResponse(credential);
    return serializePkcWithAssertionToJson(credential);
  } catch (err) {
    throw handlePasskeyAuthenticationError(err);
  }
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/foundation/factories/serviceClients/cognitoIdentityProvider/createConfirmDeviceClient.mjs
var createConfirmDeviceClient = (config) => composeServiceApi(cognitoUserPoolTransferHandler, createUserPoolSerializer("ConfirmDevice"), createUserPoolDeserializer(), {
  ...DEFAULT_SERVICE_CLIENT_API_CONFIG,
  ...config
});

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/textEncoder/index.mjs
var textEncoder = {
  convert(input) {
    return new TextEncoder().encode(input);
  }
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/BigInteger/BigInteger.mjs
function BigInteger(a, b) {
  if (a != null)
    this.fromString(a, b);
}
function nbi() {
  return new BigInteger(null, null);
}
var dbits;
var canary = 244837814094590;
var j_lm = (canary & 16777215) === 15715070;
function am1(i, x, w, j, c, n) {
  while (--n >= 0) {
    const v = x * this[i++] + w[j] + c;
    c = Math.floor(v / 67108864);
    w[j++] = v & 67108863;
  }
  return c;
}
function am2(i, x, w, j, c, n) {
  const xl = x & 32767;
  const xh = x >> 15;
  while (--n >= 0) {
    let l = this[i] & 32767;
    const h = this[i++] >> 15;
    const m = xh * l + h * xl;
    l = xl * l + ((m & 32767) << 15) + w[j] + (c & 1073741823);
    c = (l >>> 30) + (m >>> 15) + xh * h + (c >>> 30);
    w[j++] = l & 1073741823;
  }
  return c;
}
function am3(i, x, w, j, c, n) {
  const xl = x & 16383;
  const xh = x >> 14;
  while (--n >= 0) {
    let l = this[i] & 16383;
    const h = this[i++] >> 14;
    const m = xh * l + h * xl;
    l = xl * l + ((m & 16383) << 14) + w[j] + c;
    c = (l >> 28) + (m >> 14) + xh * h;
    w[j++] = l & 268435455;
  }
  return c;
}
var inBrowser = typeof navigator !== "undefined";
if (inBrowser && j_lm && navigator.appName === "Microsoft Internet Explorer") {
  BigInteger.prototype.am = am2;
  dbits = 30;
} else if (inBrowser && j_lm && navigator.appName !== "Netscape") {
  BigInteger.prototype.am = am1;
  dbits = 26;
} else {
  BigInteger.prototype.am = am3;
  dbits = 28;
}
BigInteger.prototype.DB = dbits;
BigInteger.prototype.DM = (1 << dbits) - 1;
BigInteger.prototype.DV = 1 << dbits;
var BI_FP = 52;
BigInteger.prototype.FV = Math.pow(2, BI_FP);
BigInteger.prototype.F1 = BI_FP - dbits;
BigInteger.prototype.F2 = 2 * dbits - BI_FP;
var BI_RM = "0123456789abcdefghijklmnopqrstuvwxyz";
var BI_RC = [];
var rr;
var vv;
rr = "0".charCodeAt(0);
for (vv = 0; vv <= 9; ++vv)
  BI_RC[rr++] = vv;
rr = "a".charCodeAt(0);
for (vv = 10; vv < 36; ++vv)
  BI_RC[rr++] = vv;
rr = "A".charCodeAt(0);
for (vv = 10; vv < 36; ++vv)
  BI_RC[rr++] = vv;
function int2char(n) {
  return BI_RM.charAt(n);
}
function intAt(s, i) {
  const c = BI_RC[s.charCodeAt(i)];
  return c == null ? -1 : c;
}
function bnpCopyTo(r) {
  for (let i = this.t - 1; i >= 0; --i)
    r[i] = this[i];
  r.t = this.t;
  r.s = this.s;
}
function bnpFromInt(x) {
  this.t = 1;
  this.s = x < 0 ? -1 : 0;
  if (x > 0)
    this[0] = x;
  else if (x < -1)
    this[0] = x + this.DV;
  else
    this.t = 0;
}
function nbv(i) {
  const r = nbi();
  r.fromInt(i);
  return r;
}
function bnpFromString(s, b) {
  let k;
  if (b === 16)
    k = 4;
  else if (b === 8)
    k = 3;
  else if (b === 2)
    k = 1;
  else if (b === 32)
    k = 5;
  else if (b === 4)
    k = 2;
  else
    throw new Error("Only radix 2, 4, 8, 16, 32 are supported");
  this.t = 0;
  this.s = 0;
  let i = s.length;
  let mi = false;
  let sh = 0;
  while (--i >= 0) {
    const x = intAt(s, i);
    if (x < 0) {
      if (s.charAt(i) === "-")
        mi = true;
      continue;
    }
    mi = false;
    if (sh === 0)
      this[this.t++] = x;
    else if (sh + k > this.DB) {
      this[this.t - 1] |= (x & (1 << this.DB - sh) - 1) << sh;
      this[this.t++] = x >> this.DB - sh;
    } else
      this[this.t - 1] |= x << sh;
    sh += k;
    if (sh >= this.DB)
      sh -= this.DB;
  }
  this.clamp();
  if (mi)
    BigInteger.ZERO.subTo(this, this);
}
function bnpClamp() {
  const c = this.s & this.DM;
  while (this.t > 0 && this[this.t - 1] == c)
    --this.t;
}
function bnToString(b) {
  if (this.s < 0)
    return "-" + this.negate().toString(b);
  let k;
  if (b == 16)
    k = 4;
  else if (b === 8)
    k = 3;
  else if (b === 2)
    k = 1;
  else if (b === 32)
    k = 5;
  else if (b === 4)
    k = 2;
  else
    throw new Error("Only radix 2, 4, 8, 16, 32 are supported");
  const km = (1 << k) - 1;
  let d;
  let m = false;
  let r = "";
  let i = this.t;
  let p = this.DB - i * this.DB % k;
  if (i-- > 0) {
    if (p < this.DB && (d = this[i] >> p) > 0) {
      m = true;
      r = int2char(d);
    }
    while (i >= 0) {
      if (p < k) {
        d = (this[i] & (1 << p) - 1) << k - p;
        d |= this[--i] >> (p += this.DB - k);
      } else {
        d = this[i] >> (p -= k) & km;
        if (p <= 0) {
          p += this.DB;
          --i;
        }
      }
      if (d > 0)
        m = true;
      if (m)
        r += int2char(d);
    }
  }
  return m ? r : "0";
}
function bnNegate() {
  const r = nbi();
  BigInteger.ZERO.subTo(this, r);
  return r;
}
function bnAbs() {
  return this.s < 0 ? this.negate() : this;
}
function bnCompareTo(a) {
  let r = this.s - a.s;
  if (r != 0)
    return r;
  let i = this.t;
  r = i - a.t;
  if (r != 0)
    return this.s < 0 ? -r : r;
  while (--i >= 0)
    if ((r = this[i] - a[i]) != 0)
      return r;
  return 0;
}
function nbits(x) {
  let r = 1;
  let t;
  if ((t = x >>> 16) !== 0) {
    x = t;
    r += 16;
  }
  if ((t = x >> 8) !== 0) {
    x = t;
    r += 8;
  }
  if ((t = x >> 4) !== 0) {
    x = t;
    r += 4;
  }
  if ((t = x >> 2) !== 0) {
    x = t;
    r += 2;
  }
  if ((t = x >> 1) !== 0) {
    x = t;
    r += 1;
  }
  return r;
}
function bnBitLength() {
  if (this.t <= 0)
    return 0;
  return this.DB * (this.t - 1) + nbits(this[this.t - 1] ^ this.s & this.DM);
}
function bnpDLShiftTo(n, r) {
  let i;
  for (i = this.t - 1; i >= 0; --i)
    r[i + n] = this[i];
  for (i = n - 1; i >= 0; --i)
    r[i] = 0;
  r.t = this.t + n;
  r.s = this.s;
}
function bnpDRShiftTo(n, r) {
  for (let i = n; i < this.t; ++i)
    r[i - n] = this[i];
  r.t = Math.max(this.t - n, 0);
  r.s = this.s;
}
function bnpLShiftTo(n, r) {
  const bs = n % this.DB;
  const cbs = this.DB - bs;
  const bm = (1 << cbs) - 1;
  const ds = Math.floor(n / this.DB);
  let c = this.s << bs & this.DM;
  let i;
  for (i = this.t - 1; i >= 0; --i) {
    r[i + ds + 1] = this[i] >> cbs | c;
    c = (this[i] & bm) << bs;
  }
  for (i = ds - 1; i >= 0; --i)
    r[i] = 0;
  r[ds] = c;
  r.t = this.t + ds + 1;
  r.s = this.s;
  r.clamp();
}
function bnpRShiftTo(n, r) {
  r.s = this.s;
  const ds = Math.floor(n / this.DB);
  if (ds >= this.t) {
    r.t = 0;
    return;
  }
  const bs = n % this.DB;
  const cbs = this.DB - bs;
  const bm = (1 << bs) - 1;
  r[0] = this[ds] >> bs;
  for (let i = ds + 1; i < this.t; ++i) {
    r[i - ds - 1] |= (this[i] & bm) << cbs;
    r[i - ds] = this[i] >> bs;
  }
  if (bs > 0)
    r[this.t - ds - 1] |= (this.s & bm) << cbs;
  r.t = this.t - ds;
  r.clamp();
}
function bnpSubTo(a, r) {
  let i = 0;
  let c = 0;
  const m = Math.min(a.t, this.t);
  while (i < m) {
    c += this[i] - a[i];
    r[i++] = c & this.DM;
    c >>= this.DB;
  }
  if (a.t < this.t) {
    c -= a.s;
    while (i < this.t) {
      c += this[i];
      r[i++] = c & this.DM;
      c >>= this.DB;
    }
    c += this.s;
  } else {
    c += this.s;
    while (i < a.t) {
      c -= a[i];
      r[i++] = c & this.DM;
      c >>= this.DB;
    }
    c -= a.s;
  }
  r.s = c < 0 ? -1 : 0;
  if (c < -1)
    r[i++] = this.DV + c;
  else if (c > 0)
    r[i++] = c;
  r.t = i;
  r.clamp();
}
function bnpMultiplyTo(a, r) {
  const x = this.abs();
  const y = a.abs();
  let i = x.t;
  r.t = i + y.t;
  while (--i >= 0)
    r[i] = 0;
  for (i = 0; i < y.t; ++i)
    r[i + x.t] = x.am(0, y[i], r, i, 0, x.t);
  r.s = 0;
  r.clamp();
  if (this.s !== a.s)
    BigInteger.ZERO.subTo(r, r);
}
function bnpSquareTo(r) {
  const x = this.abs();
  let i = r.t = 2 * x.t;
  while (--i >= 0)
    r[i] = 0;
  for (i = 0; i < x.t - 1; ++i) {
    const c = x.am(i, x[i], r, 2 * i, 0, 1);
    if ((r[i + x.t] += x.am(i + 1, 2 * x[i], r, 2 * i + 1, c, x.t - i - 1)) >= x.DV) {
      r[i + x.t] -= x.DV;
      r[i + x.t + 1] = 1;
    }
  }
  if (r.t > 0)
    r[r.t - 1] += x.am(i, x[i], r, 2 * i, 0, 1);
  r.s = 0;
  r.clamp();
}
function bnpDivRemTo(m, q, r) {
  const pm = m.abs();
  if (pm.t <= 0)
    return;
  const pt = this.abs();
  if (pt.t < pm.t) {
    if (q != null)
      q.fromInt(0);
    if (r != null)
      this.copyTo(r);
    return;
  }
  if (r === null)
    r = nbi();
  const y = nbi();
  const ts = this.s;
  const ms = m.s;
  const nsh = this.DB - nbits(pm[pm.t - 1]);
  if (nsh > 0) {
    pm.lShiftTo(nsh, y);
    pt.lShiftTo(nsh, r);
  } else {
    pm.copyTo(y);
    pt.copyTo(r);
  }
  const ys = y.t;
  const y0 = y[ys - 1];
  if (y0 === 0)
    return;
  const yt = y0 * (1 << this.F1) + (ys > 1 ? y[ys - 2] >> this.F2 : 0);
  const d1 = this.FV / yt;
  const d2 = (1 << this.F1) / yt;
  const e = 1 << this.F2;
  let i = r.t;
  let j = i - ys;
  const t = q === null ? nbi() : q;
  y.dlShiftTo(j, t);
  if (r.compareTo(t) >= 0) {
    r[r.t++] = 1;
    r.subTo(t, r);
  }
  BigInteger.ONE.dlShiftTo(ys, t);
  t.subTo(y, y);
  while (y.t < ys)
    y[y.t++] = 0;
  while (--j >= 0) {
    let qd = r[--i] === y0 ? this.DM : Math.floor(r[i] * d1 + (r[i - 1] + e) * d2);
    if ((r[i] += y.am(0, qd, r, j, 0, ys)) < qd) {
      y.dlShiftTo(j, t);
      r.subTo(t, r);
      while (r[i] < --qd)
        r.subTo(t, r);
    }
  }
  if (q !== null) {
    r.drShiftTo(ys, q);
    if (ts !== ms)
      BigInteger.ZERO.subTo(q, q);
  }
  r.t = ys;
  r.clamp();
  if (nsh > 0)
    r.rShiftTo(nsh, r);
  if (ts < 0)
    BigInteger.ZERO.subTo(r, r);
}
function bnMod(a) {
  const r = nbi();
  this.abs().divRemTo(a, null, r);
  if (this.s < 0 && r.compareTo(BigInteger.ZERO) > 0)
    a.subTo(r, r);
  return r;
}
function bnpInvDigit() {
  if (this.t < 1)
    return 0;
  const x = this[0];
  if ((x & 1) === 0)
    return 0;
  let y = x & 3;
  y = y * (2 - (x & 15) * y) & 15;
  y = y * (2 - (x & 255) * y) & 255;
  y = y * (2 - ((x & 65535) * y & 65535)) & 65535;
  y = y * (2 - x * y % this.DV) % this.DV;
  return y > 0 ? this.DV - y : -y;
}
function bnEquals(a) {
  return this.compareTo(a) === 0;
}
function bnpAddTo(a, r) {
  let i = 0;
  let c = 0;
  const m = Math.min(a.t, this.t);
  while (i < m) {
    c += this[i] + a[i];
    r[i++] = c & this.DM;
    c >>= this.DB;
  }
  if (a.t < this.t) {
    c += a.s;
    while (i < this.t) {
      c += this[i];
      r[i++] = c & this.DM;
      c >>= this.DB;
    }
    c += this.s;
  } else {
    c += this.s;
    while (i < a.t) {
      c += a[i];
      r[i++] = c & this.DM;
      c >>= this.DB;
    }
    c += a.s;
  }
  r.s = c < 0 ? -1 : 0;
  if (c > 0)
    r[i++] = c;
  else if (c < -1)
    r[i++] = this.DV + c;
  r.t = i;
  r.clamp();
}
function bnAdd(a) {
  const r = nbi();
  this.addTo(a, r);
  return r;
}
function bnSubtract(a) {
  const r = nbi();
  this.subTo(a, r);
  return r;
}
function bnMultiply(a) {
  const r = nbi();
  this.multiplyTo(a, r);
  return r;
}
function bnDivide(a) {
  const r = nbi();
  this.divRemTo(a, r, null);
  return r;
}
function Montgomery(m) {
  this.m = m;
  this.mp = m.invDigit();
  this.mpl = this.mp & 32767;
  this.mph = this.mp >> 15;
  this.um = (1 << m.DB - 15) - 1;
  this.mt2 = 2 * m.t;
}
function montConvert(x) {
  const r = nbi();
  x.abs().dlShiftTo(this.m.t, r);
  r.divRemTo(this.m, null, r);
  if (x.s < 0 && r.compareTo(BigInteger.ZERO) > 0)
    this.m.subTo(r, r);
  return r;
}
function montRevert(x) {
  const r = nbi();
  x.copyTo(r);
  this.reduce(r);
  return r;
}
function montReduce(x) {
  while (x.t <= this.mt2)
    x[x.t++] = 0;
  for (let i = 0; i < this.m.t; ++i) {
    let j = x[i] & 32767;
    const u0 = j * this.mpl + ((j * this.mph + (x[i] >> 15) * this.mpl & this.um) << 15) & x.DM;
    j = i + this.m.t;
    x[j] += this.m.am(0, u0, x, i, 0, this.m.t);
    while (x[j] >= x.DV) {
      x[j] -= x.DV;
      x[++j]++;
    }
  }
  x.clamp();
  x.drShiftTo(this.m.t, x);
  if (x.compareTo(this.m) >= 0)
    x.subTo(this.m, x);
}
function montSqrTo(x, r) {
  x.squareTo(r);
  this.reduce(r);
}
function montMulTo(x, y, r) {
  x.multiplyTo(y, r);
  this.reduce(r);
}
Montgomery.prototype.convert = montConvert;
Montgomery.prototype.revert = montRevert;
Montgomery.prototype.reduce = montReduce;
Montgomery.prototype.mulTo = montMulTo;
Montgomery.prototype.sqrTo = montSqrTo;
function bnModPow(e, m, callback) {
  let i = e.bitLength();
  let k;
  let r = nbv(1);
  const z = new Montgomery(m);
  if (i <= 0)
    return r;
  else if (i < 18)
    k = 1;
  else if (i < 48)
    k = 3;
  else if (i < 144)
    k = 4;
  else if (i < 768)
    k = 5;
  else
    k = 6;
  const g = [];
  let n = 3;
  const k1 = k - 1;
  const km = (1 << k) - 1;
  g[1] = z.convert(this);
  if (k > 1) {
    const g2 = nbi();
    z.sqrTo(g[1], g2);
    while (n <= km) {
      g[n] = nbi();
      z.mulTo(g2, g[n - 2], g[n]);
      n += 2;
    }
  }
  let j = e.t - 1;
  let w;
  let is1 = true;
  let r2 = nbi();
  let t;
  i = nbits(e[j]) - 1;
  while (j >= 0) {
    if (i >= k1)
      w = e[j] >> i - k1 & km;
    else {
      w = (e[j] & (1 << i + 1) - 1) << k1 - i;
      if (j > 0)
        w |= e[j - 1] >> this.DB + i - k1;
    }
    n = k;
    while ((w & 1) === 0) {
      w >>= 1;
      --n;
    }
    if ((i -= n) < 0) {
      i += this.DB;
      --j;
    }
    if (is1) {
      g[w].copyTo(r);
      is1 = false;
    } else {
      while (n > 1) {
        z.sqrTo(r, r2);
        z.sqrTo(r2, r);
        n -= 2;
      }
      if (n > 0)
        z.sqrTo(r, r2);
      else {
        t = r;
        r = r2;
        r2 = t;
      }
      z.mulTo(r2, g[w], r);
    }
    while (j >= 0 && (e[j] & 1 << i) === 0) {
      z.sqrTo(r, r2);
      t = r;
      r = r2;
      r2 = t;
      if (--i < 0) {
        i = this.DB - 1;
        --j;
      }
    }
  }
  const result = z.revert(r);
  callback(null, result);
  return result;
}
BigInteger.prototype.copyTo = bnpCopyTo;
BigInteger.prototype.fromInt = bnpFromInt;
BigInteger.prototype.fromString = bnpFromString;
BigInteger.prototype.clamp = bnpClamp;
BigInteger.prototype.dlShiftTo = bnpDLShiftTo;
BigInteger.prototype.drShiftTo = bnpDRShiftTo;
BigInteger.prototype.lShiftTo = bnpLShiftTo;
BigInteger.prototype.rShiftTo = bnpRShiftTo;
BigInteger.prototype.subTo = bnpSubTo;
BigInteger.prototype.multiplyTo = bnpMultiplyTo;
BigInteger.prototype.squareTo = bnpSquareTo;
BigInteger.prototype.divRemTo = bnpDivRemTo;
BigInteger.prototype.invDigit = bnpInvDigit;
BigInteger.prototype.addTo = bnpAddTo;
BigInteger.prototype.toString = bnToString;
BigInteger.prototype.negate = bnNegate;
BigInteger.prototype.abs = bnAbs;
BigInteger.prototype.compareTo = bnCompareTo;
BigInteger.prototype.bitLength = bnBitLength;
BigInteger.prototype.mod = bnMod;
BigInteger.prototype.equals = bnEquals;
BigInteger.prototype.add = bnAdd;
BigInteger.prototype.subtract = bnSubtract;
BigInteger.prototype.multiply = bnMultiply;
BigInteger.prototype.divide = bnDivide;
BigInteger.prototype.modPow = bnModPow;
BigInteger.ZERO = nbv(0);
BigInteger.ONE = nbv(1);

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/calculate/calculateS.mjs
var calculateS = async ({ a, g, k, x, B, N, U }) => {
  return new Promise((resolve, reject) => {
    g.modPow(x, N, (outerErr, outerResult) => {
      if (outerErr) {
        reject(outerErr);
        return;
      }
      B.subtract(k.multiply(outerResult)).modPow(a.add(U.multiply(x)), N, (innerErr, innerResult) => {
        if (innerErr) {
          reject(innerErr);
          return;
        }
        resolve(innerResult.mod(N));
      });
    });
  });
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/constants.mjs
var INIT_N = "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6BF12FFA06D98A0864D87602733EC86A64521F2B18177B200CBBE117577A615D6C770988C0BAD946E208E24FA074E5AB3143DB5BFCE0FD108E4B82D120A93AD2CAFFFFFFFFFFFFFFFF";
var SHORT_TO_HEX = {};
var HEX_TO_SHORT = {};
for (let i = 0; i < 256; i++) {
  let encodedByte = i.toString(16).toLowerCase();
  if (encodedByte.length === 1) {
    encodedByte = `0${encodedByte}`;
  }
  SHORT_TO_HEX[i] = encodedByte;
  HEX_TO_SHORT[encodedByte] = i;
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/getBytesFromHex.mjs
var getBytesFromHex = (encoded) => {
  if (encoded.length % 2 !== 0) {
    throw new Error("Hex encoded strings must have an even number length");
  }
  const out = new Uint8Array(encoded.length / 2);
  for (let i = 0; i < encoded.length; i += 2) {
    const encodedByte = encoded.slice(i, i + 2).toLowerCase();
    if (encodedByte in HEX_TO_SHORT) {
      out[i / 2] = HEX_TO_SHORT[encodedByte];
    } else {
      throw new Error(`Cannot decode unrecognized sequence ${encodedByte} as hexadecimal`);
    }
  }
  return out;
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/getHexFromBytes.mjs
var getHexFromBytes = (bytes) => {
  let out = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    out += SHORT_TO_HEX[bytes[i]];
  }
  return out;
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/getHashFromData.mjs
var getHashFromData = (data) => {
  const sha256 = new Sha256();
  sha256.update(data);
  const hashedData = sha256.digestSync();
  const hashHexFromUint8 = getHexFromBytes(hashedData);
  return new Array(64 - hashHexFromUint8.length).join("0") + hashHexFromUint8;
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/getHashFromHex.mjs
var getHashFromHex = (hexStr) => getHashFromData(getBytesFromHex(hexStr));

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/getPaddedHex.mjs
var HEX_MSB_REGEX = /^[89a-f]/i;
var getPaddedHex = (bigInt) => {
  if (!(bigInt instanceof BigInteger)) {
    throw new Error("Not a BigInteger");
  }
  const isNegative = bigInt.compareTo(BigInteger.ZERO) < 0;
  let hexStr = bigInt.abs().toString(16);
  hexStr = hexStr.length % 2 !== 0 ? `0${hexStr}` : hexStr;
  hexStr = HEX_MSB_REGEX.test(hexStr) ? `00${hexStr}` : hexStr;
  if (isNegative) {
    const invertedNibbles = hexStr.split("").map((x) => {
      const invertedNibble = ~parseInt(x, 16) & 15;
      return "0123456789ABCDEF".charAt(invertedNibble);
    }).join("");
    const flippedBitsBI = new BigInteger(invertedNibbles, 16).add(BigInteger.ONE);
    hexStr = flippedBitsBI.toString(16);
    if (hexStr.toUpperCase().startsWith("FF8")) {
      hexStr = hexStr.substring(2);
    }
  }
  return hexStr;
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/calculate/calculateU.mjs
var calculateU = ({ A, B }) => {
  const U = new BigInteger(getHashFromHex(getPaddedHex(A) + getPaddedHex(B)), 16);
  if (U.equals(BigInteger.ZERO)) {
    throw new Error("U cannot be zero.");
  }
  return U;
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/getHkdfKey.mjs
var getHkdfKey = (ikm, salt, info) => {
  const awsCryptoHash = new Sha256(salt);
  awsCryptoHash.update(ikm);
  const resultFromAWSCryptoPrk = awsCryptoHash.digestSync();
  const awsCryptoHashHmac = new Sha256(resultFromAWSCryptoPrk);
  awsCryptoHashHmac.update(info);
  const resultFromAWSCryptoHmac = awsCryptoHashHmac.digestSync();
  const hashHexFromAWSCrypto = resultFromAWSCryptoHmac;
  return hashHexFromAWSCrypto.slice(0, 16);
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/getRandomBytes.mjs
var getRandomBytes = (nBytes) => {
  const str = new WordArray().random(nBytes).toString();
  return getBytesFromHex(str);
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/getRandomString.mjs
var getRandomString = () => base64Encoder.convert(getRandomBytes(40));

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/AuthenticationHelper/AuthenticationHelper.mjs
var AuthenticationHelper = class {
  constructor({ userPoolName, a, g, A, N }) {
    this.encoder = textEncoder;
    this.userPoolName = userPoolName;
    this.a = a;
    this.g = g;
    this.A = A;
    this.N = N;
    this.k = new BigInteger(getHashFromHex(`${getPaddedHex(N)}${getPaddedHex(g)}`), 16);
  }
  /**
   * @returns {string} Generated random value included in password hash.
   */
  getRandomPassword() {
    if (!this.randomPassword) {
      throw new AuthError({
        name: "EmptyBigIntegerRandomPassword",
        message: "random password is empty"
      });
    }
    return this.randomPassword;
  }
  /**
   * @returns {string} Generated random value included in devices hash.
   */
  getSaltToHashDevices() {
    if (!this.saltToHashDevices) {
      throw new AuthError({
        name: "EmptyBigIntegersaltToHashDevices",
        message: "saltToHashDevices is empty"
      });
    }
    return this.saltToHashDevices;
  }
  /**
   * @returns {string} Value used to verify devices.
   */
  getVerifierDevices() {
    if (!this.verifierDevices) {
      throw new AuthError({
        name: "EmptyBigIntegerVerifierDevices",
        message: "verifyDevices is empty"
      });
    }
    return this.verifierDevices;
  }
  /**
   * Generate salts and compute verifier.
   *
   * @param {string} deviceGroupKey Devices to generate verifier for.
   * @param {string} username User to generate verifier for.
   *
   * @returns {Promise<void>}
   */
  async generateHashDevice(deviceGroupKey, username) {
    this.randomPassword = getRandomString();
    const combinedString = `${deviceGroupKey}${username}:${this.randomPassword}`;
    const hashedString = getHashFromData(combinedString);
    const hexRandom = getHexFromBytes(getRandomBytes(16));
    this.saltToHashDevices = getPaddedHex(new BigInteger(hexRandom, 16));
    return new Promise((resolve, reject) => {
      this.g.modPow(new BigInteger(getHashFromHex(this.saltToHashDevices + hashedString), 16), this.N, (err, result) => {
        if (err) {
          reject(err);
          return;
        }
        this.verifierDevices = getPaddedHex(result);
        resolve();
      });
    });
  }
  /**
   * Calculates the final HKDF key based on computed S value, computed U value and the key
   *
   * @param {String} username Username.
   * @param {String} password Password.
   * @param {AuthBigInteger} B Server B value.
   * @param {AuthBigInteger} salt Generated salt.
   */
  async getPasswordAuthenticationKey({ username, password, serverBValue, salt }) {
    if (serverBValue.mod(this.N).equals(BigInteger.ZERO)) {
      throw new Error("B cannot be zero.");
    }
    const U = calculateU({
      A: this.A,
      B: serverBValue
    });
    const usernamePassword = `${this.userPoolName}${username}:${password}`;
    const usernamePasswordHash = getHashFromData(usernamePassword);
    const x = new BigInteger(getHashFromHex(getPaddedHex(salt) + usernamePasswordHash), 16);
    const S = await calculateS({
      a: this.a,
      g: this.g,
      k: this.k,
      x,
      B: serverBValue,
      N: this.N,
      U
    });
    const context = this.encoder.convert("Caldera Derived Key");
    const spacer = this.encoder.convert(String.fromCharCode(1));
    const info = new Uint8Array(context.byteLength + spacer.byteLength);
    info.set(context, 0);
    info.set(spacer, context.byteLength);
    const hkdfKey = getHkdfKey(getBytesFromHex(getPaddedHex(S)), getBytesFromHex(getPaddedHex(U)), info);
    return hkdfKey;
  }
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/calculate/calculateA.mjs
var calculateA = async ({ a, g, N }) => {
  return new Promise((resolve, reject) => {
    g.modPow(a, N, (err, A) => {
      if (err) {
        reject(err);
        return;
      }
      if (A.mod(N).equals(BigInteger.ZERO)) {
        reject(new Error("Illegal parameter. A mod N cannot be 0."));
        return;
      }
      resolve(A);
    });
  });
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/getAuthenticationHelper.mjs
var getAuthenticationHelper = async (userPoolName) => {
  const N = new BigInteger(INIT_N, 16);
  const g = new BigInteger("2", 16);
  const a = generateRandomBigInteger();
  const A = await calculateA({ a, g, N });
  return new AuthenticationHelper({ userPoolName, a, g, A, N });
};
var generateRandomBigInteger = () => {
  const hexRandom = getHexFromBytes(getRandomBytes(128));
  return new BigInteger(hexRandom, 16);
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/getNewDeviceMetadata.mjs
async function getNewDeviceMetadata({ userPoolId, userPoolEndpoint, newDeviceMetadata, accessToken }) {
  if (!newDeviceMetadata)
    return void 0;
  const userPoolName = userPoolId.split("_")[1] || "";
  const authenticationHelper = await getAuthenticationHelper(userPoolName);
  const deviceKey = newDeviceMetadata == null ? void 0 : newDeviceMetadata.DeviceKey;
  const deviceGroupKey = newDeviceMetadata == null ? void 0 : newDeviceMetadata.DeviceGroupKey;
  try {
    await authenticationHelper.generateHashDevice(deviceGroupKey ?? "", deviceKey ?? "");
  } catch (errGenHash) {
    return void 0;
  }
  const deviceSecretVerifierConfig = {
    Salt: base64Encoder.convert(getBytesFromHex(authenticationHelper.getSaltToHashDevices())),
    PasswordVerifier: base64Encoder.convert(getBytesFromHex(authenticationHelper.getVerifierDevices()))
  };
  const randomPassword = authenticationHelper.getRandomPassword();
  try {
    const confirmDevice = createConfirmDeviceClient({
      endpointResolver: createCognitoUserPoolEndpointResolver({
        endpointOverride: userPoolEndpoint
      })
    });
    await confirmDevice({ region: getRegionFromUserPoolId(userPoolId) }, {
      AccessToken: accessToken,
      DeviceName: await getDeviceName(),
      DeviceKey: newDeviceMetadata == null ? void 0 : newDeviceMetadata.DeviceKey,
      DeviceSecretVerifierConfig: deviceSecretVerifierConfig
    });
    return {
      deviceKey,
      deviceGroupKey,
      randomPassword
    };
  } catch (error) {
    return void 0;
  }
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/client/flows/userAuth/handleWebAuthnSignInResult.mjs
async function handleWebAuthnSignInResult(challengeParameters) {
  var _a;
  const authConfig = (_a = Amplify.getConfig().Auth) == null ? void 0 : _a.Cognito;
  assertTokenProviderConfig(authConfig);
  const { username, signInSession, signInDetails, challengeName } = signInStore.getState();
  if (challengeName !== "WEB_AUTHN" || !username) {
    throw new AuthError({
      name: AuthErrorCodes.SignInException,
      message: "Unable to proceed due to invalid sign in state."
    });
  }
  const { CREDENTIAL_REQUEST_OPTIONS: credentialRequestOptions } = challengeParameters;
  assertPasskeyError(!!credentialRequestOptions, PasskeyErrorCode.InvalidPasskeyAuthenticationOptions);
  const cred = await getPasskey(JSON.parse(credentialRequestOptions));
  const respondToAuthChallenge = createRespondToAuthChallengeClient({
    endpointResolver: createCognitoUserPoolEndpointResolver({
      endpointOverride: authConfig.userPoolEndpoint
    })
  });
  const { ChallengeName: nextChallengeName, ChallengeParameters: nextChallengeParameters, AuthenticationResult: authenticationResult, Session: nextSession } = await respondToAuthChallenge({
    region: getRegionFromUserPoolId(authConfig.userPoolId),
    userAgentValue: getAuthUserAgentValue(AuthAction.ConfirmSignIn)
  }, {
    ChallengeName: "WEB_AUTHN",
    ChallengeResponses: {
      USERNAME: username,
      CREDENTIAL: JSON.stringify(cred)
    },
    ClientId: authConfig.userPoolClientId,
    Session: signInSession
  });
  setActiveSignInState({
    signInSession: nextSession,
    username,
    challengeName: nextChallengeName,
    signInDetails
  });
  if (authenticationResult) {
    await cacheCognitoTokens({
      ...authenticationResult,
      username,
      NewDeviceMetadata: await getNewDeviceMetadata({
        userPoolId: authConfig.userPoolId,
        userPoolEndpoint: authConfig.userPoolEndpoint,
        newDeviceMetadata: authenticationResult.NewDeviceMetadata,
        accessToken: authenticationResult.AccessToken
      }),
      signInDetails
    });
    signInStore.dispatch({ type: "RESET_STATE" });
    await dispatchSignedInHubEvent();
    return {
      isSignedIn: true,
      nextStep: { signInStep: "DONE" }
    };
  }
  if (nextChallengeName === "WEB_AUTHN") {
    throw new AuthError({
      name: AuthErrorCodes.SignInException,
      message: "Sequential WEB_AUTHN challenges returned from underlying service cannot be handled."
    });
  }
  return {
    challengeName: nextChallengeName,
    challengeParameters: nextChallengeParameters
  };
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/userContextData.mjs
function getUserContextData({ username, userPoolId, userPoolClientId }) {
  if (typeof window === "undefined") {
    return void 0;
  }
  const amazonCognitoAdvancedSecurityData = window.AmazonCognitoAdvancedSecurityData;
  if (typeof amazonCognitoAdvancedSecurityData === "undefined") {
    return void 0;
  }
  const advancedSecurityData = amazonCognitoAdvancedSecurityData.getData(username, userPoolId, userPoolClientId);
  if (advancedSecurityData) {
    const userContextData = {
      EncodedData: advancedSecurityData
    };
    return userContextData;
  }
  return {};
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/getNowString.mjs
var MONTH_NAMES = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec"
];
var WEEK_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
var getNowString = () => {
  const now = /* @__PURE__ */ new Date();
  const weekDay = WEEK_NAMES[now.getUTCDay()];
  const month = MONTH_NAMES[now.getUTCMonth()];
  const day = now.getUTCDate();
  let hours = now.getUTCHours();
  if (hours < 10) {
    hours = `0${hours}`;
  }
  let minutes = now.getUTCMinutes();
  if (minutes < 10) {
    minutes = `0${minutes}`;
  }
  let seconds = now.getUTCSeconds();
  if (seconds < 10) {
    seconds = `0${seconds}`;
  }
  const year = now.getUTCFullYear();
  const dateNow = `${weekDay} ${month} ${day} ${hours}:${minutes}:${seconds} UTC ${year}`;
  return dateNow;
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/srp/getSignatureString.mjs
var getSignatureString = ({ userPoolName, username, challengeParameters, dateNow, hkdf }) => {
  const bufUPIDaToB = textEncoder.convert(userPoolName);
  const bufUNaToB = textEncoder.convert(username);
  const bufSBaToB = urlB64ToUint8Array(challengeParameters.SECRET_BLOCK);
  const bufDNaToB = textEncoder.convert(dateNow);
  const bufConcat = new Uint8Array(bufUPIDaToB.byteLength + bufUNaToB.byteLength + bufSBaToB.byteLength + bufDNaToB.byteLength);
  bufConcat.set(bufUPIDaToB, 0);
  bufConcat.set(bufUNaToB, bufUPIDaToB.byteLength);
  bufConcat.set(bufSBaToB, bufUPIDaToB.byteLength + bufUNaToB.byteLength);
  bufConcat.set(bufDNaToB, bufUPIDaToB.byteLength + bufUNaToB.byteLength + bufSBaToB.byteLength);
  const awsCryptoHash = new Sha256(hkdf);
  awsCryptoHash.update(bufConcat);
  const resultFromAWSCrypto = awsCryptoHash.digestSync();
  const signatureString = base64Encoder.convert(resultFromAWSCrypto);
  return signatureString;
};
var urlB64ToUint8Array = (base64String) => {
  const padding = "=".repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = base64Decoder.convert(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/handleDeviceSRPAuth.mjs
async function handleDeviceSRPAuth({ username, config, clientMetadata, session, tokenOrchestrator: tokenOrchestrator2 }) {
  const { userPoolId, userPoolEndpoint } = config;
  const clientId = config.userPoolClientId;
  const deviceMetadata = await (tokenOrchestrator2 == null ? void 0 : tokenOrchestrator2.getDeviceMetadata(username));
  assertDeviceMetadata(deviceMetadata);
  const authenticationHelper = await getAuthenticationHelper(deviceMetadata.deviceGroupKey);
  const challengeResponses = {
    USERNAME: username,
    SRP_A: authenticationHelper.A.toString(16),
    DEVICE_KEY: deviceMetadata.deviceKey
  };
  const jsonReqResponseChallenge = {
    ChallengeName: "DEVICE_SRP_AUTH",
    ClientId: clientId,
    ChallengeResponses: challengeResponses,
    ClientMetadata: clientMetadata,
    Session: session
  };
  const respondToAuthChallenge = createRespondToAuthChallengeClient({
    endpointResolver: createCognitoUserPoolEndpointResolver({
      endpointOverride: userPoolEndpoint
    })
  });
  const { ChallengeParameters: respondedChallengeParameters, Session } = await respondToAuthChallenge({ region: getRegionFromUserPoolId(userPoolId) }, jsonReqResponseChallenge);
  return handleDevicePasswordVerifier(username, respondedChallengeParameters, clientMetadata, Session, authenticationHelper, config, tokenOrchestrator2);
}
async function handleDevicePasswordVerifier(username, challengeParameters, clientMetadata, session, authenticationHelper, { userPoolId, userPoolClientId, userPoolEndpoint }, tokenOrchestrator2) {
  const deviceMetadata = await (tokenOrchestrator2 == null ? void 0 : tokenOrchestrator2.getDeviceMetadata(username));
  assertDeviceMetadata(deviceMetadata);
  const serverBValue = new BigInteger(challengeParameters == null ? void 0 : challengeParameters.SRP_B, 16);
  const salt = new BigInteger(challengeParameters == null ? void 0 : challengeParameters.SALT, 16);
  const { deviceKey } = deviceMetadata;
  const { deviceGroupKey } = deviceMetadata;
  const hkdf = await authenticationHelper.getPasswordAuthenticationKey({
    username: deviceMetadata.deviceKey,
    password: deviceMetadata.randomPassword,
    serverBValue,
    salt
  });
  const dateNow = getNowString();
  const challengeResponses = {
    USERNAME: (challengeParameters == null ? void 0 : challengeParameters.USERNAME) ?? username,
    PASSWORD_CLAIM_SECRET_BLOCK: challengeParameters == null ? void 0 : challengeParameters.SECRET_BLOCK,
    TIMESTAMP: dateNow,
    PASSWORD_CLAIM_SIGNATURE: getSignatureString({
      username: deviceKey,
      userPoolName: deviceGroupKey,
      challengeParameters,
      dateNow,
      hkdf
    }),
    DEVICE_KEY: deviceKey
  };
  const UserContextData = getUserContextData({
    username,
    userPoolId,
    userPoolClientId
  });
  const jsonReqResponseChallenge = {
    ChallengeName: "DEVICE_PASSWORD_VERIFIER",
    ClientId: userPoolClientId,
    ChallengeResponses: challengeResponses,
    Session: session,
    ClientMetadata: clientMetadata,
    UserContextData
  };
  const respondToAuthChallenge = createRespondToAuthChallengeClient({
    endpointResolver: createCognitoUserPoolEndpointResolver({
      endpointOverride: userPoolEndpoint
    })
  });
  return respondToAuthChallenge({ region: getRegionFromUserPoolId(userPoolId) }, jsonReqResponseChallenge);
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/handlePasswordVerifierChallenge.mjs
async function handlePasswordVerifierChallenge(password, challengeParameters, clientMetadata, session, authenticationHelper, config, tokenOrchestrator2) {
  const { userPoolId, userPoolClientId, userPoolEndpoint } = config;
  const userPoolName = (userPoolId == null ? void 0 : userPoolId.split("_")[1]) || "";
  const serverBValue = new BigInteger(challengeParameters == null ? void 0 : challengeParameters.SRP_B, 16);
  const salt = new BigInteger(challengeParameters == null ? void 0 : challengeParameters.SALT, 16);
  const username = challengeParameters == null ? void 0 : challengeParameters.USER_ID_FOR_SRP;
  if (!username)
    throw new AuthError({
      name: "EmptyUserIdForSRPException",
      message: "USER_ID_FOR_SRP was not found in challengeParameters"
    });
  const hkdf = await authenticationHelper.getPasswordAuthenticationKey({
    username,
    password,
    serverBValue,
    salt
  });
  const dateNow = getNowString();
  const challengeResponses = {
    USERNAME: username,
    PASSWORD_CLAIM_SECRET_BLOCK: challengeParameters == null ? void 0 : challengeParameters.SECRET_BLOCK,
    TIMESTAMP: dateNow,
    PASSWORD_CLAIM_SIGNATURE: getSignatureString({
      username,
      userPoolName,
      challengeParameters,
      dateNow,
      hkdf
    })
  };
  const deviceMetadata = await tokenOrchestrator2.getDeviceMetadata(username);
  if (deviceMetadata && deviceMetadata.deviceKey) {
    challengeResponses.DEVICE_KEY = deviceMetadata.deviceKey;
  }
  const UserContextData = getUserContextData({
    username,
    userPoolId,
    userPoolClientId
  });
  const jsonReqResponseChallenge = {
    ChallengeName: "PASSWORD_VERIFIER",
    ChallengeResponses: challengeResponses,
    ClientMetadata: clientMetadata,
    Session: session,
    ClientId: userPoolClientId,
    UserContextData
  };
  const respondToAuthChallenge = createRespondToAuthChallengeClient({
    endpointResolver: createCognitoUserPoolEndpointResolver({
      endpointOverride: userPoolEndpoint
    })
  });
  const response = await respondToAuthChallenge({ region: getRegionFromUserPoolId(userPoolId) }, jsonReqResponseChallenge);
  if (response.ChallengeName === "DEVICE_SRP_AUTH")
    return handleDeviceSRPAuth({
      username,
      config,
      clientMetadata,
      session: response.Session,
      tokenOrchestrator: tokenOrchestrator2
    });
  return response;
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/retryOnResourceNotFoundException.mjs
async function retryOnResourceNotFoundException(func, args, username, tokenOrchestrator2) {
  try {
    return await func(...args);
  } catch (error) {
    if (error instanceof AuthError && error.name === "ResourceNotFoundException" && error.message.includes("Device does not exist.")) {
      await tokenOrchestrator2.clearDeviceMetadata(username);
      return func(...args);
    }
    throw error;
  }
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/setActiveSignInUsername.mjs
function setActiveSignInUsername(username) {
  const { dispatch } = signInStore;
  dispatch({ type: "SET_USERNAME", value: username });
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/client/flows/shared/handlePasswordSRP.mjs
async function handlePasswordSRP({ username, password, clientMetadata, config, tokenOrchestrator: tokenOrchestrator2, authFlow, preferredChallenge }) {
  const { userPoolId, userPoolClientId, userPoolEndpoint } = config;
  const userPoolName = (userPoolId == null ? void 0 : userPoolId.split("_")[1]) || "";
  const authenticationHelper = await getAuthenticationHelper(userPoolName);
  const authParameters = {
    USERNAME: username,
    SRP_A: authenticationHelper.A.toString(16)
  };
  if (authFlow === "USER_AUTH" && preferredChallenge) {
    authParameters.PREFERRED_CHALLENGE = preferredChallenge;
  }
  const UserContextData = getUserContextData({
    username,
    userPoolId,
    userPoolClientId
  });
  const jsonReq = {
    AuthFlow: authFlow,
    AuthParameters: authParameters,
    ClientMetadata: clientMetadata,
    ClientId: userPoolClientId,
    UserContextData
  };
  const initiateAuth = createInitiateAuthClient({
    endpointResolver: createCognitoUserPoolEndpointResolver({
      endpointOverride: userPoolEndpoint
    })
  });
  const resp = await initiateAuth({
    region: getRegionFromUserPoolId(userPoolId),
    userAgentValue: getAuthUserAgentValue(AuthAction.SignIn)
  }, jsonReq);
  const { ChallengeParameters: challengeParameters, Session: session } = resp;
  const activeUsername = (challengeParameters == null ? void 0 : challengeParameters.USERNAME) ?? username;
  setActiveSignInUsername(activeUsername);
  if (resp.ChallengeName === "PASSWORD_VERIFIER") {
    return retryOnResourceNotFoundException(handlePasswordVerifierChallenge, [
      password,
      challengeParameters,
      clientMetadata,
      session,
      authenticationHelper,
      config,
      tokenOrchestrator2
    ], activeUsername, tokenOrchestrator2);
  }
  return resp;
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/signInHelpers.mjs
var USER_ATTRIBUTES = "userAttributes.";
function isWebAuthnResultAuthSignInOutput(result) {
  return "isSignedIn" in result && "nextStep" in result;
}
async function handleUserPasswordAuthFlow(username, password, clientMetadata, config, tokenOrchestrator2) {
  var _a, _b;
  const { userPoolClientId, userPoolId, userPoolEndpoint } = config;
  const authParameters = {
    USERNAME: username,
    PASSWORD: password
  };
  const deviceMetadata = await tokenOrchestrator2.getDeviceMetadata(username);
  if (deviceMetadata && deviceMetadata.deviceKey) {
    authParameters.DEVICE_KEY = deviceMetadata.deviceKey;
  }
  const UserContextData = getUserContextData({
    username,
    userPoolId,
    userPoolClientId
  });
  const jsonReq = {
    AuthFlow: "USER_PASSWORD_AUTH",
    AuthParameters: authParameters,
    ClientMetadata: clientMetadata,
    ClientId: userPoolClientId,
    UserContextData
  };
  const initiateAuth = createInitiateAuthClient({
    endpointResolver: createCognitoUserPoolEndpointResolver({
      endpointOverride: userPoolEndpoint
    })
  });
  const response = await initiateAuth({
    region: getRegionFromUserPoolId(userPoolId),
    userAgentValue: getAuthUserAgentValue(AuthAction.SignIn)
  }, jsonReq);
  const activeUsername = ((_a = response.ChallengeParameters) == null ? void 0 : _a.USERNAME) ?? ((_b = response.ChallengeParameters) == null ? void 0 : _b.USER_ID_FOR_SRP) ?? username;
  setActiveSignInUsername(activeUsername);
  if (response.ChallengeName === "DEVICE_SRP_AUTH")
    return handleDeviceSRPAuth({
      username: activeUsername,
      config,
      clientMetadata,
      session: response.Session,
      tokenOrchestrator: tokenOrchestrator2
    });
  return response;
}
async function handleUserSRPAuthFlow(username, password, clientMetadata, config, tokenOrchestrator2) {
  return handlePasswordSRP({
    username,
    password,
    clientMetadata,
    config,
    tokenOrchestrator: tokenOrchestrator2,
    authFlow: "USER_SRP_AUTH"
  });
}
async function handleCustomAuthFlowWithoutSRP(username, clientMetadata, config, tokenOrchestrator2) {
  var _a;
  const { userPoolClientId, userPoolId, userPoolEndpoint } = config;
  const authParameters = {
    USERNAME: username
  };
  const deviceMetadata = await tokenOrchestrator2.getDeviceMetadata(username);
  if (deviceMetadata && deviceMetadata.deviceKey) {
    authParameters.DEVICE_KEY = deviceMetadata.deviceKey;
  }
  const UserContextData = getUserContextData({
    username,
    userPoolId,
    userPoolClientId
  });
  const jsonReq = {
    AuthFlow: "CUSTOM_AUTH",
    AuthParameters: authParameters,
    ClientMetadata: clientMetadata,
    ClientId: userPoolClientId,
    UserContextData
  };
  const initiateAuth = createInitiateAuthClient({
    endpointResolver: createCognitoUserPoolEndpointResolver({
      endpointOverride: userPoolEndpoint
    })
  });
  const response = await initiateAuth({
    region: getRegionFromUserPoolId(userPoolId),
    userAgentValue: getAuthUserAgentValue(AuthAction.SignIn)
  }, jsonReq);
  const activeUsername = ((_a = response.ChallengeParameters) == null ? void 0 : _a.USERNAME) ?? username;
  setActiveSignInUsername(activeUsername);
  if (response.ChallengeName === "DEVICE_SRP_AUTH")
    return handleDeviceSRPAuth({
      username: activeUsername,
      config,
      clientMetadata,
      session: response.Session,
      tokenOrchestrator: tokenOrchestrator2
    });
  return response;
}
async function handleCustomSRPAuthFlow(username, password, clientMetadata, config, tokenOrchestrator2) {
  assertTokenProviderConfig(config);
  const { userPoolId, userPoolClientId, userPoolEndpoint } = config;
  const userPoolName = (userPoolId == null ? void 0 : userPoolId.split("_")[1]) || "";
  const authenticationHelper = await getAuthenticationHelper(userPoolName);
  const authParameters = {
    USERNAME: username,
    SRP_A: authenticationHelper.A.toString(16),
    CHALLENGE_NAME: "SRP_A"
  };
  const UserContextData = getUserContextData({
    username,
    userPoolId,
    userPoolClientId
  });
  const jsonReq = {
    AuthFlow: "CUSTOM_AUTH",
    AuthParameters: authParameters,
    ClientMetadata: clientMetadata,
    ClientId: userPoolClientId,
    UserContextData
  };
  const initiateAuth = createInitiateAuthClient({
    endpointResolver: createCognitoUserPoolEndpointResolver({
      endpointOverride: userPoolEndpoint
    })
  });
  const { ChallengeParameters: challengeParameters, Session: session } = await initiateAuth({
    region: getRegionFromUserPoolId(userPoolId),
    userAgentValue: getAuthUserAgentValue(AuthAction.SignIn)
  }, jsonReq);
  const activeUsername = (challengeParameters == null ? void 0 : challengeParameters.USERNAME) ?? username;
  setActiveSignInUsername(activeUsername);
  return retryOnResourceNotFoundException(handlePasswordVerifierChallenge, [
    password,
    challengeParameters,
    clientMetadata,
    session,
    authenticationHelper,
    config,
    tokenOrchestrator2
  ], activeUsername, tokenOrchestrator2);
}
async function getSignInResult(params) {
  var _a;
  const { challengeName, challengeParameters, availableChallenges } = params;
  const authConfig = (_a = Amplify.getConfig().Auth) == null ? void 0 : _a.Cognito;
  assertTokenProviderConfig(authConfig);
  switch (challengeName) {
    case "CUSTOM_CHALLENGE":
      return {
        isSignedIn: false,
        nextStep: {
          signInStep: "CONFIRM_SIGN_IN_WITH_CUSTOM_CHALLENGE",
          additionalInfo: challengeParameters
        }
      };
    case "MFA_SETUP": {
      const { signInSession, username } = signInStore.getState();
      const mfaSetupTypes = getMFATypes(parseMFATypes(challengeParameters.MFAS_CAN_SETUP)) || [];
      const allowedMfaSetupTypes = getAllowedMfaSetupTypes(mfaSetupTypes);
      const isTotpMfaSetupAvailable = allowedMfaSetupTypes.includes("TOTP");
      const isEmailMfaSetupAvailable = allowedMfaSetupTypes.includes("EMAIL");
      if (isTotpMfaSetupAvailable && isEmailMfaSetupAvailable) {
        return {
          isSignedIn: false,
          nextStep: {
            signInStep: "CONTINUE_SIGN_IN_WITH_MFA_SETUP_SELECTION",
            allowedMFATypes: allowedMfaSetupTypes
          }
        };
      }
      if (isEmailMfaSetupAvailable) {
        return {
          isSignedIn: false,
          nextStep: {
            signInStep: "CONTINUE_SIGN_IN_WITH_EMAIL_SETUP"
          }
        };
      }
      if (isTotpMfaSetupAvailable) {
        const associateSoftwareToken = createAssociateSoftwareTokenClient({
          endpointResolver: createCognitoUserPoolEndpointResolver({
            endpointOverride: authConfig.userPoolEndpoint
          })
        });
        const { Session, SecretCode: secretCode } = await associateSoftwareToken({ region: getRegionFromUserPoolId(authConfig.userPoolId) }, {
          Session: signInSession
        });
        signInStore.dispatch({
          type: "SET_SIGN_IN_SESSION",
          value: Session
        });
        return {
          isSignedIn: false,
          nextStep: {
            signInStep: "CONTINUE_SIGN_IN_WITH_TOTP_SETUP",
            totpSetupDetails: getTOTPSetupDetails(secretCode, username)
          }
        };
      }
      throw new AuthError({
        name: AuthErrorCodes.SignInException,
        message: `Cannot initiate MFA setup from available types: ${mfaSetupTypes}`
      });
    }
    case "NEW_PASSWORD_REQUIRED":
      return {
        isSignedIn: false,
        nextStep: {
          signInStep: "CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED",
          missingAttributes: parseAttributes(challengeParameters.requiredAttributes)
        }
      };
    case "SELECT_MFA_TYPE":
      return {
        isSignedIn: false,
        nextStep: {
          signInStep: "CONTINUE_SIGN_IN_WITH_MFA_SELECTION",
          allowedMFATypes: getMFATypes(parseMFATypes(challengeParameters.MFAS_CAN_CHOOSE))
        }
      };
    case "SMS_OTP":
    case "SMS_MFA":
      return {
        isSignedIn: false,
        nextStep: {
          signInStep: "CONFIRM_SIGN_IN_WITH_SMS_CODE",
          codeDeliveryDetails: {
            deliveryMedium: challengeParameters.CODE_DELIVERY_DELIVERY_MEDIUM,
            destination: challengeParameters.CODE_DELIVERY_DESTINATION
          }
        }
      };
    case "SOFTWARE_TOKEN_MFA":
      return {
        isSignedIn: false,
        nextStep: {
          signInStep: "CONFIRM_SIGN_IN_WITH_TOTP_CODE"
        }
      };
    case "EMAIL_OTP":
      return {
        isSignedIn: false,
        nextStep: {
          signInStep: "CONFIRM_SIGN_IN_WITH_EMAIL_CODE",
          codeDeliveryDetails: {
            deliveryMedium: challengeParameters.CODE_DELIVERY_DELIVERY_MEDIUM,
            destination: challengeParameters.CODE_DELIVERY_DESTINATION
          }
        }
      };
    case "WEB_AUTHN": {
      const result = await handleWebAuthnSignInResult(challengeParameters);
      if (isWebAuthnResultAuthSignInOutput(result)) {
        return result;
      }
      return getSignInResult(result);
    }
    case "PASSWORD":
    case "PASSWORD_SRP":
      return {
        isSignedIn: false,
        nextStep: {
          signInStep: "CONFIRM_SIGN_IN_WITH_PASSWORD"
        }
      };
    case "SELECT_CHALLENGE":
      return {
        isSignedIn: false,
        nextStep: {
          signInStep: "CONTINUE_SIGN_IN_WITH_FIRST_FACTOR_SELECTION",
          availableChallenges
        }
      };
  }
  throw new AuthError({
    name: AuthErrorCodes.SignInException,
    message: `An error occurred during the sign in process. ${challengeName} challengeName returned by the underlying service was not addressed.`
  });
}
function getTOTPSetupDetails(secretCode, username) {
  return {
    sharedSecret: secretCode,
    getSetupUri: (appName, accountName) => {
      const totpUri = `otpauth://totp/${appName}:${accountName ?? username}?secret=${secretCode}&issuer=${appName}`;
      return new AmplifyUrl(totpUri);
    }
  };
}
function getSignInResultFromError(errorName) {
  if (errorName === InitiateAuthException.PasswordResetRequiredException) {
    return {
      isSignedIn: false,
      nextStep: { signInStep: "RESET_PASSWORD" }
    };
  } else if (errorName === InitiateAuthException.UserNotConfirmedException) {
    return {
      isSignedIn: false,
      nextStep: { signInStep: "CONFIRM_SIGN_UP" }
    };
  }
}
function parseAttributes(attributes) {
  if (!attributes)
    return [];
  const parsedAttributes = JSON.parse(attributes).map((att) => att.includes(USER_ATTRIBUTES) ? att.replace(USER_ATTRIBUTES, "") : att);
  return parsedAttributes;
}
function getMFAType(type) {
  if (type === "SMS_MFA")
    return "SMS";
  if (type === "SOFTWARE_TOKEN_MFA")
    return "TOTP";
  if (type === "EMAIL_OTP")
    return "EMAIL";
}
function getMFATypes(types) {
  if (!types)
    return void 0;
  return types.map(getMFAType).filter(Boolean);
}
function parseMFATypes(mfa) {
  if (!mfa)
    return [];
  return JSON.parse(mfa);
}
function getAllowedMfaSetupTypes(availableMfaSetupTypes) {
  return availableMfaSetupTypes.filter((authMfaType) => authMfaType === "EMAIL" || authMfaType === "TOTP");
}
async function assertUserNotAuthenticated() {
  let authUser;
  try {
    authUser = await getCurrentUser2();
  } catch (error) {
  }
  if (authUser && authUser.userId && authUser.username) {
    throw new AuthError({
      name: USER_ALREADY_AUTHENTICATED_EXCEPTION,
      message: "There is already a signed in user.",
      recoverySuggestion: "Call signOut before calling signIn again."
    });
  }
}
function getActiveSignInUsername(username) {
  const state = signInStore.getState();
  return state.username ?? username;
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/apis/signInWithCustomAuth.mjs
async function signInWithCustomAuth(input) {
  var _a;
  const authConfig = (_a = Amplify.getConfig().Auth) == null ? void 0 : _a.Cognito;
  assertTokenProviderConfig(authConfig);
  const { username, password, options } = input;
  const signInDetails = {
    loginId: username,
    authFlowType: "CUSTOM_WITHOUT_SRP"
  };
  const metadata = options == null ? void 0 : options.clientMetadata;
  assertValidationError(!!username, AuthValidationErrorCode.EmptySignInUsername);
  assertValidationError(!password, AuthValidationErrorCode.CustomAuthSignInPassword);
  try {
    const { ChallengeName: retriedChallengeName, ChallengeParameters: retiredChallengeParameters, AuthenticationResult, Session } = await retryOnResourceNotFoundException(handleCustomAuthFlowWithoutSRP, [username, metadata, authConfig, tokenOrchestrator], username, tokenOrchestrator);
    const activeUsername = getActiveSignInUsername(username);
    setActiveSignInState({
      signInSession: Session,
      username: activeUsername,
      challengeName: retriedChallengeName,
      signInDetails
    });
    if (AuthenticationResult) {
      await cacheCognitoTokens({
        username: activeUsername,
        ...AuthenticationResult,
        NewDeviceMetadata: await getNewDeviceMetadata({
          userPoolId: authConfig.userPoolId,
          userPoolEndpoint: authConfig.userPoolEndpoint,
          newDeviceMetadata: AuthenticationResult.NewDeviceMetadata,
          accessToken: AuthenticationResult.AccessToken
        }),
        signInDetails
      });
      resetActiveSignInState();
      await dispatchSignedInHubEvent();
      return {
        isSignedIn: true,
        nextStep: { signInStep: "DONE" }
      };
    }
    return getSignInResult({
      challengeName: retriedChallengeName,
      challengeParameters: retiredChallengeParameters
    });
  } catch (error) {
    resetActiveSignInState();
    assertServiceError(error);
    const result = getSignInResultFromError(error.name);
    if (result)
      return result;
    throw error;
  }
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/apis/signInWithCustomSRPAuth.mjs
async function signInWithCustomSRPAuth(input) {
  var _a;
  const { username, password, options } = input;
  const signInDetails = {
    loginId: username,
    authFlowType: "CUSTOM_WITH_SRP"
  };
  const authConfig = (_a = Amplify.getConfig().Auth) == null ? void 0 : _a.Cognito;
  assertTokenProviderConfig(authConfig);
  const metadata = options == null ? void 0 : options.clientMetadata;
  assertValidationError(!!username, AuthValidationErrorCode.EmptySignInUsername);
  assertValidationError(!!password, AuthValidationErrorCode.EmptySignInPassword);
  try {
    const { ChallengeName: handledChallengeName, ChallengeParameters: handledChallengeParameters, AuthenticationResult, Session } = await handleCustomSRPAuthFlow(username, password, metadata, authConfig, tokenOrchestrator);
    const activeUsername = getActiveSignInUsername(username);
    setActiveSignInState({
      signInSession: Session,
      username: activeUsername,
      challengeName: handledChallengeName,
      signInDetails
    });
    if (AuthenticationResult) {
      await cacheCognitoTokens({
        username: activeUsername,
        ...AuthenticationResult,
        NewDeviceMetadata: await getNewDeviceMetadata({
          userPoolId: authConfig.userPoolId,
          userPoolEndpoint: authConfig.userPoolEndpoint,
          newDeviceMetadata: AuthenticationResult.NewDeviceMetadata,
          accessToken: AuthenticationResult.AccessToken
        }),
        signInDetails
      });
      resetActiveSignInState();
      await dispatchSignedInHubEvent();
      return {
        isSignedIn: true,
        nextStep: { signInStep: "DONE" }
      };
    }
    return getSignInResult({
      challengeName: handledChallengeName,
      challengeParameters: handledChallengeParameters
    });
  } catch (error) {
    resetActiveSignInState();
    assertServiceError(error);
    const result = getSignInResultFromError(error.name);
    if (result)
      return result;
    throw error;
  }
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/apis/autoSignIn.mjs
var initialAutoSignIn = async () => {
  throw new AuthError({
    name: AUTO_SIGN_IN_EXCEPTION,
    message: "The autoSignIn flow has not started, or has been cancelled/completed.",
    recoverySuggestion: "Please try to use the signIn API or log out before starting a new autoSignIn flow."
  });
};
var autoSignIn = initialAutoSignIn;
function resetAutoSignIn(resetCallback = true) {
  if (resetCallback) {
    autoSignIn = initialAutoSignIn;
  }
  autoSignInStore.dispatch({ type: "RESET" });
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/apis/signInWithSRP.mjs
async function signInWithSRP(input) {
  var _a, _b;
  const { username, password } = input;
  const authConfig = (_a = Amplify.getConfig().Auth) == null ? void 0 : _a.Cognito;
  const signInDetails = {
    loginId: username,
    authFlowType: "USER_SRP_AUTH"
  };
  assertTokenProviderConfig(authConfig);
  const clientMetaData = (_b = input.options) == null ? void 0 : _b.clientMetadata;
  assertValidationError(!!username, AuthValidationErrorCode.EmptySignInUsername);
  assertValidationError(!!password, AuthValidationErrorCode.EmptySignInPassword);
  try {
    const { ChallengeName: handledChallengeName, ChallengeParameters: handledChallengeParameters, AuthenticationResult, Session } = await handleUserSRPAuthFlow(username, password, clientMetaData, authConfig, tokenOrchestrator);
    const activeUsername = getActiveSignInUsername(username);
    setActiveSignInState({
      signInSession: Session,
      username: activeUsername,
      challengeName: handledChallengeName,
      signInDetails
    });
    if (AuthenticationResult) {
      await cacheCognitoTokens({
        username: activeUsername,
        ...AuthenticationResult,
        NewDeviceMetadata: await getNewDeviceMetadata({
          userPoolId: authConfig.userPoolId,
          userPoolEndpoint: authConfig.userPoolEndpoint,
          newDeviceMetadata: AuthenticationResult.NewDeviceMetadata,
          accessToken: AuthenticationResult.AccessToken
        }),
        signInDetails
      });
      resetActiveSignInState();
      await dispatchSignedInHubEvent();
      resetAutoSignIn();
      return {
        isSignedIn: true,
        nextStep: { signInStep: "DONE" }
      };
    }
    return getSignInResult({
      challengeName: handledChallengeName,
      challengeParameters: handledChallengeParameters
    });
  } catch (error) {
    resetActiveSignInState();
    resetAutoSignIn();
    assertServiceError(error);
    const result = getSignInResultFromError(error.name);
    if (result)
      return result;
    throw error;
  }
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/apis/signInWithUserPassword.mjs
async function signInWithUserPassword(input) {
  var _a;
  const { username, password, options } = input;
  const authConfig = (_a = Amplify.getConfig().Auth) == null ? void 0 : _a.Cognito;
  const signInDetails = {
    loginId: username,
    authFlowType: "USER_PASSWORD_AUTH"
  };
  assertTokenProviderConfig(authConfig);
  const metadata = options == null ? void 0 : options.clientMetadata;
  assertValidationError(!!username, AuthValidationErrorCode.EmptySignInUsername);
  assertValidationError(!!password, AuthValidationErrorCode.EmptySignInPassword);
  try {
    const { ChallengeName: retiredChallengeName, ChallengeParameters: retriedChallengeParameters, AuthenticationResult, Session } = await retryOnResourceNotFoundException(handleUserPasswordAuthFlow, [username, password, metadata, authConfig, tokenOrchestrator], username, tokenOrchestrator);
    const activeUsername = getActiveSignInUsername(username);
    setActiveSignInState({
      signInSession: Session,
      username: activeUsername,
      challengeName: retiredChallengeName,
      signInDetails
    });
    if (AuthenticationResult) {
      await cacheCognitoTokens({
        ...AuthenticationResult,
        username: activeUsername,
        NewDeviceMetadata: await getNewDeviceMetadata({
          userPoolId: authConfig.userPoolId,
          userPoolEndpoint: authConfig.userPoolEndpoint,
          newDeviceMetadata: AuthenticationResult.NewDeviceMetadata,
          accessToken: AuthenticationResult.AccessToken
        }),
        signInDetails
      });
      resetActiveSignInState();
      await dispatchSignedInHubEvent();
      resetAutoSignIn();
      return {
        isSignedIn: true,
        nextStep: { signInStep: "DONE" }
      };
    }
    return getSignInResult({
      challengeName: retiredChallengeName,
      challengeParameters: retriedChallengeParameters
    });
  } catch (error) {
    resetActiveSignInState();
    resetAutoSignIn();
    assertServiceError(error);
    const result = getSignInResultFromError(error.name);
    if (result)
      return result;
    throw error;
  }
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/client/flows/userAuth/handleUserAuthFlow.mjs
async function handleUserAuthFlow({ username, clientMetadata, config, tokenOrchestrator: tokenOrchestrator2, preferredChallenge, password, session }) {
  const { userPoolId, userPoolClientId, userPoolEndpoint } = config;
  const UserContextData = getUserContextData({
    username,
    userPoolId,
    userPoolClientId
  });
  const authParameters = { USERNAME: username };
  if (preferredChallenge) {
    if (config.passwordless) {
      const isInvalidChallenge = preferredChallenge === "EMAIL_OTP" && !config.passwordless.emailOtpEnabled || preferredChallenge === "SMS_OTP" && !config.passwordless.smsOtpEnabled || preferredChallenge === "WEB_AUTHN" && !config.passwordless.webAuthn;
      if (isInvalidChallenge) {
        assertValidationError(false, AuthValidationErrorCode.InvalidPreferredChallenge);
      }
    }
    if (preferredChallenge === "PASSWORD_SRP") {
      assertValidationError(!!password, AuthValidationErrorCode.EmptySignInPassword);
      return handlePasswordSRP({
        username,
        password,
        clientMetadata,
        config,
        tokenOrchestrator: tokenOrchestrator2,
        authFlow: "USER_AUTH",
        preferredChallenge
      });
    }
    if (preferredChallenge === "PASSWORD") {
      assertValidationError(!!password, AuthValidationErrorCode.EmptySignInPassword);
      authParameters.PASSWORD = password;
    }
    authParameters.PREFERRED_CHALLENGE = preferredChallenge;
  }
  const jsonReq = {
    AuthFlow: "USER_AUTH",
    AuthParameters: authParameters,
    ClientMetadata: clientMetadata,
    ClientId: userPoolClientId,
    UserContextData
  };
  if (session) {
    jsonReq.Session = session;
  }
  const initiateAuth = createInitiateAuthClient({
    endpointResolver: createCognitoUserPoolEndpointResolver({
      endpointOverride: userPoolEndpoint
    })
  });
  const response = await initiateAuth({
    region: getRegionFromUserPoolId(userPoolId),
    userAgentValue: getAuthUserAgentValue(AuthAction.SignIn)
  }, jsonReq);
  setActiveSignInUsername(username);
  return response;
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/apis/signInWithUserAuth.mjs
async function signInWithUserAuth(input) {
  var _a, _b;
  const { username, password, options } = input;
  const authConfig = (_a = Amplify.getConfig().Auth) == null ? void 0 : _a.Cognito;
  const signInDetails = {
    loginId: username,
    authFlowType: "USER_AUTH"
  };
  assertTokenProviderConfig(authConfig);
  const clientMetaData = options == null ? void 0 : options.clientMetadata;
  const preferredChallenge = (options == null ? void 0 : options.preferredChallenge) ?? ((_b = authConfig == null ? void 0 : authConfig.passwordless) == null ? void 0 : _b.preferredChallenge);
  assertValidationError(!!username, AuthValidationErrorCode.EmptySignInUsername);
  try {
    const handleUserAuthFlowInput = {
      username,
      config: authConfig,
      tokenOrchestrator,
      clientMetadata: clientMetaData,
      preferredChallenge,
      password
    };
    const autoSignInStoreState = autoSignInStore.getState();
    if (autoSignInStoreState.active && autoSignInStoreState.username === username) {
      handleUserAuthFlowInput.session = autoSignInStoreState.session;
    }
    const response = await handleUserAuthFlow(handleUserAuthFlowInput);
    const activeUsername = getActiveSignInUsername(username);
    setActiveSignInState({
      signInSession: response.Session,
      username: activeUsername,
      challengeName: response.ChallengeName,
      signInDetails
    });
    if (response.AuthenticationResult) {
      await cacheCognitoTokens({
        username: activeUsername,
        ...response.AuthenticationResult,
        NewDeviceMetadata: await getNewDeviceMetadata({
          userPoolId: authConfig.userPoolId,
          userPoolEndpoint: authConfig.userPoolEndpoint,
          newDeviceMetadata: response.AuthenticationResult.NewDeviceMetadata,
          accessToken: response.AuthenticationResult.AccessToken
        }),
        signInDetails
      });
      resetActiveSignInState();
      await dispatchSignedInHubEvent();
      resetAutoSignIn();
      return {
        isSignedIn: true,
        nextStep: { signInStep: "DONE" }
      };
    }
    return getSignInResult({
      challengeName: response.ChallengeName,
      challengeParameters: response.ChallengeParameters,
      availableChallenges: "AvailableChallenges" in response ? response.AvailableChallenges : void 0
    });
  } catch (error) {
    resetActiveSignInState();
    resetAutoSignIn();
    assertServiceError(error);
    const result = getSignInResultFromError(error.name);
    if (result)
      return result;
    throw error;
  }
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/apis/signIn.mjs
async function signIn(input) {
  var _a;
  resetAutoSignIn(false);
  const authFlowType = (_a = input.options) == null ? void 0 : _a.authFlowType;
  await assertUserNotAuthenticated();
  switch (authFlowType) {
    case "USER_SRP_AUTH":
      return signInWithSRP(input);
    case "USER_PASSWORD_AUTH":
      return signInWithUserPassword(input);
    case "CUSTOM_WITHOUT_SRP":
      return signInWithCustomAuth(input);
    case "CUSTOM_WITH_SRP":
      return signInWithCustomSRPAuth(input);
    case "USER_AUTH":
      return signInWithUserAuth(input);
    default:
      return signInWithSRP(input);
  }
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/signUpHelpers.mjs
var MAX_AUTOSIGNIN_POLLING_MS = 3 * 60 * 1e3;
function debounce(fun, delay) {
  let timer;
  return (args) => {
    if (!timer) {
      fun(...args);
    }
    clearTimeout(timer);
    timer = setTimeout(() => {
      timer = void 0;
    }, delay);
  };
}
function handleAutoSignInWithLink(signInInput, resolve, reject) {
  const start = Date.now();
  const autoSignInPollingIntervalId = setInterval(async () => {
    const elapsedTime = Date.now() - start;
    const maxTime = MAX_AUTOSIGNIN_POLLING_MS;
    if (elapsedTime > maxTime) {
      clearInterval(autoSignInPollingIntervalId);
      reject(new AuthError({
        name: AUTO_SIGN_IN_EXCEPTION,
        message: "The account was not confirmed on time.",
        recoverySuggestion: "Try to verify your account by clicking the link sent your email or phone and then login manually."
      }));
      resetAutoSignIn();
    } else {
      try {
        const signInOutput = await signIn(signInInput);
        if (signInOutput.nextStep.signInStep !== "CONFIRM_SIGN_UP") {
          resolve(signInOutput);
          clearInterval(autoSignInPollingIntervalId);
          resetAutoSignIn();
        }
      } catch (error) {
        clearInterval(autoSignInPollingIntervalId);
        reject(error);
        resetAutoSignIn();
      }
    }
  }, 5e3);
}
var debouncedAutoSignInWithLink = debounce(handleAutoSignInWithLink, 300);
var debouncedAutoSignWithCodeOrUserConfirmed = debounce(handleAutoSignInWithCodeOrUserConfirmed, 300);
async function handleAutoSignInWithCodeOrUserConfirmed(signInInput, resolve, reject) {
  var _a;
  try {
    const output = ((_a = signInInput == null ? void 0 : signInInput.options) == null ? void 0 : _a.authFlowType) === "USER_AUTH" ? await signInWithUserAuth(signInInput) : await signIn(signInInput);
    resolve(output);
    resetAutoSignIn();
  } catch (error) {
    reject(error);
    resetAutoSignIn();
  }
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/Errors.mjs
var logger = new ConsoleLogger("AuthError");
var authErrorMessages = {
  oauthSignInError: {
    message: AuthErrorStrings.OAUTH_ERROR,
    log: "Make sure Cognito Hosted UI has been configured correctly"
  },
  noConfig: {
    message: AuthErrorStrings.DEFAULT_MSG,
    log: `
            Error: Amplify has not been configured correctly.
            This error is typically caused by one of the following scenarios:

            1. Make sure you're passing the awsconfig object to Amplify.configure() in your app's entry point
                See https://aws-amplify.github.io/docs/js/authentication#configure-your-app for more information
            
            2. There might be multiple conflicting versions of amplify packages in your node_modules.
				Refer to our docs site for help upgrading Amplify packages (https://docs.amplify.aws/lib/troubleshooting/upgrading/q/platform/js)
        `
  },
  missingAuthConfig: {
    message: AuthErrorStrings.DEFAULT_MSG,
    log: `
            Error: Amplify has not been configured correctly. 
            The configuration object is missing required auth properties.
            This error is typically caused by one of the following scenarios:

            1. Did you run \`amplify push\` after adding auth via \`amplify add auth\`?
                See https://aws-amplify.github.io/docs/js/authentication#amplify-project-setup for more information

            2. This could also be caused by multiple conflicting versions of amplify packages, see (https://docs.amplify.aws/lib/troubleshooting/upgrading/q/platform/js) for help upgrading Amplify packages.
        `
  },
  emptyUsername: {
    message: AuthErrorStrings.EMPTY_USERNAME
  },
  // TODO: should include a list of valid sign-in types
  invalidUsername: {
    message: AuthErrorStrings.INVALID_USERNAME
  },
  emptyPassword: {
    message: AuthErrorStrings.EMPTY_PASSWORD
  },
  emptyCode: {
    message: AuthErrorStrings.EMPTY_CODE
  },
  signUpError: {
    message: AuthErrorStrings.SIGN_UP_ERROR,
    log: "The first parameter should either be non-null string or object"
  },
  noMFA: {
    message: AuthErrorStrings.NO_MFA
  },
  invalidMFA: {
    message: AuthErrorStrings.INVALID_MFA
  },
  emptyChallengeResponse: {
    message: AuthErrorStrings.EMPTY_CHALLENGE
  },
  noUserSession: {
    message: AuthErrorStrings.NO_USER_SESSION
  },
  deviceConfig: {
    message: AuthErrorStrings.DEVICE_CONFIG
  },
  networkError: {
    message: AuthErrorStrings.NETWORK_ERROR
  },
  autoSignInError: {
    message: AuthErrorStrings.AUTOSIGNIN_ERROR
  },
  default: {
    message: AuthErrorStrings.DEFAULT_MSG
  }
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/oauth/createOAuthError.mjs
var createOAuthError = (message, recoverySuggestion) => new AuthError({
  message: message ?? "An error has occurred during the oauth process.",
  name: AuthErrorCodes.OAuthSignInError,
  recoverySuggestion: recoverySuggestion ?? authErrorMessages.oauthSignInError.log
});

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/types/Auth.mjs
var AuthErrorTypes;
(function(AuthErrorTypes2) {
  AuthErrorTypes2["NoConfig"] = "noConfig";
  AuthErrorTypes2["MissingAuthConfig"] = "missingAuthConfig";
  AuthErrorTypes2["EmptyUsername"] = "emptyUsername";
  AuthErrorTypes2["InvalidUsername"] = "invalidUsername";
  AuthErrorTypes2["EmptyPassword"] = "emptyPassword";
  AuthErrorTypes2["EmptyCode"] = "emptyCode";
  AuthErrorTypes2["SignUpError"] = "signUpError";
  AuthErrorTypes2["NoMFA"] = "noMFA";
  AuthErrorTypes2["InvalidMFA"] = "invalidMFA";
  AuthErrorTypes2["EmptyChallengeResponse"] = "emptyChallengeResponse";
  AuthErrorTypes2["NoUserSession"] = "noUserSession";
  AuthErrorTypes2["Default"] = "default";
  AuthErrorTypes2["DeviceConfig"] = "deviceConfig";
  AuthErrorTypes2["NetworkError"] = "networkError";
  AuthErrorTypes2["AutoSignInError"] = "autoSignInError";
  AuthErrorTypes2["OAuthSignInError"] = "oauthSignInError";
})(AuthErrorTypes || (AuthErrorTypes = {}));

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/oauth/validateState.mjs
var flowCancelledMessage = "`signInWithRedirect` has been canceled.";
var validationFailedMessage = "An error occurred while validating the state.";
var validationRecoverySuggestion = "Try to initiate an OAuth flow from Amplify";
var validateState = async (state) => {
  const savedState = await oAuthStore.loadOAuthState();
  const validatedState = state === savedState ? savedState : void 0;
  if (!validatedState) {
    throw new AuthError({
      name: AuthErrorTypes.OAuthSignInError,
      message: state === null ? flowCancelledMessage : validationFailedMessage,
      recoverySuggestion: state === null ? void 0 : validationRecoverySuggestion
    });
  }
  return validatedState;
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/oauth/completeOAuthFlow.mjs
var completeOAuthFlow = async ({ currentUrl, userAgentValue, clientId, redirectUri, responseType, domain, preferPrivateSession }) => {
  const urlParams = new AmplifyUrl(currentUrl);
  const error = urlParams.searchParams.get("error");
  const errorMessage = urlParams.searchParams.get("error_description");
  if (error) {
    throw createOAuthError(errorMessage ?? error);
  }
  if (responseType === "code") {
    return handleCodeFlow({
      currentUrl,
      userAgentValue,
      clientId,
      redirectUri,
      domain,
      preferPrivateSession
    });
  }
  return handleImplicitFlow({
    currentUrl,
    redirectUri,
    preferPrivateSession
  });
};
var handleCodeFlow = async ({ currentUrl, userAgentValue, clientId, redirectUri, domain, preferPrivateSession }) => {
  const url = new AmplifyUrl(currentUrl);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  if (!code || !state) {
    throw createOAuthError("User cancelled OAuth flow.");
  }
  const validatedState = await validateState(state);
  const oAuthTokenEndpoint = "https://" + domain + "/oauth2/token";
  const codeVerifier = await oAuthStore.loadPKCE();
  const oAuthTokenBody = {
    grant_type: "authorization_code",
    code,
    client_id: clientId,
    redirect_uri: redirectUri,
    ...codeVerifier ? { code_verifier: codeVerifier } : {}
  };
  const body = Object.entries(oAuthTokenBody).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join("&");
  const { access_token, refresh_token: refreshToken, id_token, error, error_message: errorMessage, token_type, expires_in } = await (await fetch(oAuthTokenEndpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      [USER_AGENT_HEADER]: userAgentValue
    },
    body
  })).json();
  if (error) {
    throw createOAuthError(errorMessage ?? error);
  }
  const username = (access_token && decodeJWT(access_token).payload.username) ?? "username";
  await cacheCognitoTokens({
    username,
    AccessToken: access_token,
    IdToken: id_token,
    RefreshToken: refreshToken
  });
  return completeFlow({
    redirectUri,
    state: validatedState,
    preferPrivateSession
  });
};
var handleImplicitFlow = async ({ currentUrl, redirectUri, preferPrivateSession }) => {
  const url = new AmplifyUrl(currentUrl);
  const { id_token, access_token, state, token_type, expires_in, error_description, error } = (url.hash ?? "#").substring(1).split("&").map((pairings) => pairings.split("=")).reduce((accum, [k, v]) => ({ ...accum, [k]: v }), {
    id_token: void 0,
    access_token: void 0,
    state: void 0,
    token_type: void 0,
    expires_in: void 0,
    error_description: void 0,
    error: void 0
  });
  if (error) {
    throw createOAuthError(error_description ?? error);
  }
  if (!access_token) {
    throw createOAuthError("No access token returned from OAuth flow.");
  }
  const validatedState = await validateState(state);
  const username = (access_token && decodeJWT(access_token).payload.username) ?? "username";
  await cacheCognitoTokens({
    username,
    AccessToken: access_token,
    IdToken: id_token
  });
  return completeFlow({
    redirectUri,
    state: validatedState,
    preferPrivateSession
  });
};
var completeFlow = async ({ redirectUri, state, preferPrivateSession }) => {
  await tokenOrchestrator.setOAuthMetadata({
    oauthSignIn: true
  });
  await oAuthStore.clearOAuthData();
  await oAuthStore.storeOAuthSignIn(true, preferPrivateSession);
  resolveAndClearInflightPromises();
  clearHistory(redirectUri);
  if (isCustomState(state)) {
    Hub.dispatch("auth", {
      event: "customOAuthState",
      data: urlSafeDecode(getCustomState(state))
    }, "Auth", AMPLIFY_SYMBOL);
  }
  Hub.dispatch("auth", { event: "signInWithRedirect" }, "Auth", AMPLIFY_SYMBOL);
  await dispatchSignedInHubEvent();
};
var isCustomState = (state) => {
  return /-/.test(state);
};
var getCustomState = (state) => {
  return state.split("-").splice(1).join("-");
};
var clearHistory = (redirectUri) => {
  if (typeof window !== "undefined" && typeof window.history !== "undefined") {
    window.history.replaceState(window.history.state, "", redirectUri);
  }
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/oauth/getRedirectUrl.mjs
function getRedirectUrl(redirects, preferredRedirectUrl) {
  if (preferredRedirectUrl) {
    const redirectUrl = redirects == null ? void 0 : redirects.find((redirect) => redirect === preferredRedirectUrl);
    if (!redirectUrl) {
      throw invalidPreferredRedirectUrlException;
    }
    return redirectUrl;
  } else {
    const redirectUrlFromTheSameOrigin = (redirects == null ? void 0 : redirects.find(isSameOriginAndPathName)) ?? (redirects == null ? void 0 : redirects.find(isTheSameDomain));
    const redirectUrlFromDifferentOrigin = (redirects == null ? void 0 : redirects.find(isHttps)) ?? (redirects == null ? void 0 : redirects.find(isHttp));
    if (redirectUrlFromTheSameOrigin) {
      return redirectUrlFromTheSameOrigin;
    } else if (redirectUrlFromDifferentOrigin) {
      throw invalidOriginException;
    }
    throw invalidRedirectException;
  }
}
var isSameOriginAndPathName = (redirect) => redirect.startsWith(String(window.location.origin + (window.location.pathname || "/")));
var isTheSameDomain = (redirect) => redirect.includes(String(window.location.hostname));
var isHttp = (redirect) => redirect.startsWith("http://");
var isHttps = (redirect) => redirect.startsWith("https://");

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/oauth/handleFailure.mjs
var handleFailure = async (error) => {
  resolveAndClearInflightPromises();
  await oAuthStore.clearOAuthInflightData();
  Hub.dispatch("auth", { event: "signInWithRedirect_failure", data: { error } }, "Auth", AMPLIFY_SYMBOL);
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/oauth/attemptCompleteOAuthFlow.mjs
var attemptCompleteOAuthFlow = async (authConfig) => {
  try {
    assertTokenProviderConfig(authConfig);
    assertOAuthConfig(authConfig);
    oAuthStore.setAuthConfig(authConfig);
  } catch (_) {
    return;
  }
  if (!await oAuthStore.loadOAuthInFlight()) {
    return;
  }
  try {
    const currentUrl = window.location.href;
    const { loginWith, userPoolClientId } = authConfig;
    const { domain, redirectSignIn, responseType } = loginWith.oauth;
    const redirectUri = getRedirectUrl(redirectSignIn);
    await completeOAuthFlow({
      currentUrl,
      clientId: userPoolClientId,
      domain,
      redirectUri,
      responseType,
      userAgentValue: getAuthUserAgentValue(AuthAction.SignInWithRedirect)
    });
  } catch (err) {
    await handleFailure(err);
  }
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/utils/oauth/enableOAuthListener.mjs
isBrowser() && (() => {
  Amplify[ADD_OAUTH_LISTENER](attemptCompleteOAuthFlow);
})();

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/apis/signOut.mjs
var logger2 = new ConsoleLogger("Auth");

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/credentialsProvider/types.mjs
var IdentityIdStorageKeys = {
  identityId: "identityId"
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/credentialsProvider/IdentityIdStore.mjs
var logger3 = new ConsoleLogger("DefaultIdentityIdStore");
var DefaultIdentityIdStore = class {
  setAuthConfig(authConfigParam) {
    assertIdentityPoolIdConfig(authConfigParam.Cognito);
    this.authConfig = authConfigParam;
    this._authKeys = createKeysForAuthStorage3("Cognito", authConfigParam.Cognito.identityPoolId);
  }
  constructor(keyValueStorage) {
    this._authKeys = {};
    this._hasGuestIdentityId = false;
    this.keyValueStorage = keyValueStorage;
  }
  async loadIdentityId() {
    var _a;
    assertIdentityPoolIdConfig((_a = this.authConfig) == null ? void 0 : _a.Cognito);
    try {
      if (this._primaryIdentityId) {
        return {
          id: this._primaryIdentityId,
          type: "primary"
        };
      } else {
        const storedIdentityId = await this.keyValueStorage.getItem(this._authKeys.identityId);
        if (storedIdentityId) {
          this._hasGuestIdentityId = true;
          return {
            id: storedIdentityId,
            type: "guest"
          };
        }
        return null;
      }
    } catch (err) {
      logger3.log("Error getting stored IdentityId.", err);
      return null;
    }
  }
  async storeIdentityId(identity) {
    var _a;
    assertIdentityPoolIdConfig((_a = this.authConfig) == null ? void 0 : _a.Cognito);
    if (identity.type === "guest") {
      this.keyValueStorage.setItem(this._authKeys.identityId, identity.id);
      this._primaryIdentityId = void 0;
      this._hasGuestIdentityId = true;
    } else {
      this._primaryIdentityId = identity.id;
      if (this._hasGuestIdentityId) {
        this.keyValueStorage.removeItem(this._authKeys.identityId);
        this._hasGuestIdentityId = false;
      }
    }
  }
  async clearIdentityId() {
    this._primaryIdentityId = void 0;
    await this.keyValueStorage.removeItem(this._authKeys.identityId);
  }
};
var createKeysForAuthStorage3 = (provider, identifier) => {
  return getAuthStorageKeys(IdentityIdStorageKeys)(`com.amplify.${provider}`, identifier);
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/factories/createCognitoIdentityPoolEndpointResolver.mjs
var createCognitoIdentityPoolEndpointResolver = ({ endpointOverride }) => (input) => {
  if (endpointOverride) {
    return { url: new AmplifyUrl(endpointOverride) };
  }
  return cognitoIdentityPoolEndpointResolver(input);
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/credentialsProvider/utils.mjs
function formLoginsMap(idToken) {
  const issuer = decodeJWT(idToken).payload.iss;
  const res = {};
  if (!issuer) {
    throw new AuthError({
      name: "InvalidIdTokenException",
      message: "Invalid Idtoken."
    });
  }
  const domainName = issuer.replace(/(^\w+:|^)\/\//, "");
  res[domainName] = idToken;
  return res;
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/credentialsProvider/IdentityIdProvider.mjs
async function cognitoIdentityIdProvider({ tokens, authConfig, identityIdStore }) {
  identityIdStore.setAuthConfig({ Cognito: authConfig });
  const identityId = await identityIdStore.loadIdentityId();
  if (identityId) {
    return identityId.id;
  }
  const logins = (tokens == null ? void 0 : tokens.idToken) ? formLoginsMap(tokens.idToken.toString()) : {};
  const generatedIdentityId = await generateIdentityId(logins, authConfig);
  identityIdStore.storeIdentityId({
    id: generatedIdentityId,
    type: tokens ? "primary" : "guest"
  });
  return generatedIdentityId;
}
async function generateIdentityId(logins, authConfig) {
  const identityPoolId = authConfig == null ? void 0 : authConfig.identityPoolId;
  const region = getRegionFromIdentityPoolId(identityPoolId);
  const getId = createGetIdClient({
    endpointResolver: createCognitoIdentityPoolEndpointResolver({
      endpointOverride: authConfig.identityPoolEndpoint
    })
  });
  let idResult;
  try {
    idResult = (await getId({
      region
    }, {
      IdentityPoolId: identityPoolId,
      Logins: logins
    })).IdentityId;
  } catch (e) {
    assertServiceError(e);
    throw new AuthError(e);
  }
  if (!idResult) {
    throw new AuthError({
      name: "GetIdResponseException",
      message: "Received undefined response from getId operation",
      recoverySuggestion: "Make sure to pass a valid identityPoolId in the configuration."
    });
  }
  return idResult;
}

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/credentialsProvider/credentialsProvider.mjs
var logger4 = new ConsoleLogger("CognitoCredentialsProvider");
var CREDENTIALS_TTL = 50 * 60 * 1e3;
var CognitoAWSCredentialsAndIdentityIdProvider = class {
  constructor(identityIdStore) {
    this._nextCredentialsRefresh = 0;
    this._identityIdStore = identityIdStore;
  }
  async clearCredentialsAndIdentityId() {
    logger4.debug("Clearing out credentials and identityId");
    this._credentialsAndIdentityId = void 0;
    await this._identityIdStore.clearIdentityId();
  }
  async clearCredentials() {
    logger4.debug("Clearing out in-memory credentials");
    this._credentialsAndIdentityId = void 0;
  }
  async getCredentialsAndIdentityId(getCredentialsOptions) {
    const isAuthenticated2 = getCredentialsOptions.authenticated;
    const { tokens } = getCredentialsOptions;
    const { authConfig } = getCredentialsOptions;
    try {
      assertIdentityPoolIdConfig(authConfig == null ? void 0 : authConfig.Cognito);
    } catch {
      return;
    }
    if (!isAuthenticated2 && !authConfig.Cognito.allowGuestAccess) {
      return;
    }
    const { forceRefresh } = getCredentialsOptions;
    const tokenHasChanged = this.hasTokenChanged(tokens);
    const identityId = await cognitoIdentityIdProvider({
      tokens,
      authConfig: authConfig.Cognito,
      identityIdStore: this._identityIdStore
    });
    if (forceRefresh || tokenHasChanged) {
      this.clearCredentials();
    }
    if (!isAuthenticated2) {
      return this.getGuestCredentials(identityId, authConfig.Cognito);
    } else {
      assertIdTokenInAuthTokens(tokens);
      return this.credsForOIDCTokens(authConfig.Cognito, tokens, identityId);
    }
  }
  async getGuestCredentials(identityId, authConfig) {
    var _a, _b;
    if (this._credentialsAndIdentityId && !this.isPastTTL() && this._credentialsAndIdentityId.isAuthenticatedCreds === false) {
      logger4.info("returning stored credentials as they neither past TTL nor expired.");
      return this._credentialsAndIdentityId;
    }
    this.clearCredentials();
    const region = getRegionFromIdentityPoolId(authConfig.identityPoolId);
    const getCredentialsForIdentity = createGetCredentialsForIdentityClient({
      endpointResolver: createCognitoIdentityPoolEndpointResolver({
        endpointOverride: authConfig.identityPoolEndpoint
      })
    });
    let clientResult;
    try {
      clientResult = await getCredentialsForIdentity({ region }, {
        IdentityId: identityId
      });
    } catch (e) {
      assertServiceError(e);
      throw new AuthError(e);
    }
    if (((_a = clientResult == null ? void 0 : clientResult.Credentials) == null ? void 0 : _a.AccessKeyId) && ((_b = clientResult == null ? void 0 : clientResult.Credentials) == null ? void 0 : _b.SecretKey)) {
      this._nextCredentialsRefresh = (/* @__PURE__ */ new Date()).getTime() + CREDENTIALS_TTL;
      const res = {
        credentials: {
          accessKeyId: clientResult.Credentials.AccessKeyId,
          secretAccessKey: clientResult.Credentials.SecretKey,
          sessionToken: clientResult.Credentials.SessionToken,
          expiration: clientResult.Credentials.Expiration
        },
        identityId
      };
      if (clientResult.IdentityId) {
        res.identityId = clientResult.IdentityId;
        this._identityIdStore.storeIdentityId({
          id: clientResult.IdentityId,
          type: "guest"
        });
      }
      this._credentialsAndIdentityId = {
        ...res,
        isAuthenticatedCreds: false
      };
      return res;
    } else {
      throw new AuthError({
        name: "CredentialsNotFoundException",
        message: `Cognito did not respond with either Credentials, AccessKeyId or SecretKey.`
      });
    }
  }
  async credsForOIDCTokens(authConfig, authTokens, identityId) {
    var _a, _b, _c;
    if (this._credentialsAndIdentityId && !this.isPastTTL() && this._credentialsAndIdentityId.isAuthenticatedCreds === true) {
      logger4.debug("returning stored credentials as they neither past TTL nor expired.");
      return this._credentialsAndIdentityId;
    }
    this.clearCredentials();
    const logins = authTokens.idToken ? formLoginsMap(authTokens.idToken.toString()) : {};
    const region = getRegionFromIdentityPoolId(authConfig.identityPoolId);
    const getCredentialsForIdentity = createGetCredentialsForIdentityClient({
      endpointResolver: createCognitoIdentityPoolEndpointResolver({
        endpointOverride: authConfig.identityPoolEndpoint
      })
    });
    let clientResult;
    try {
      clientResult = await getCredentialsForIdentity({ region }, {
        IdentityId: identityId,
        Logins: logins
      });
    } catch (e) {
      assertServiceError(e);
      throw new AuthError(e);
    }
    if (((_a = clientResult == null ? void 0 : clientResult.Credentials) == null ? void 0 : _a.AccessKeyId) && ((_b = clientResult == null ? void 0 : clientResult.Credentials) == null ? void 0 : _b.SecretKey)) {
      this._nextCredentialsRefresh = (/* @__PURE__ */ new Date()).getTime() + CREDENTIALS_TTL;
      const res = {
        credentials: {
          accessKeyId: clientResult.Credentials.AccessKeyId,
          secretAccessKey: clientResult.Credentials.SecretKey,
          sessionToken: clientResult.Credentials.SessionToken,
          expiration: clientResult.Credentials.Expiration
        },
        identityId
      };
      if (clientResult.IdentityId) {
        res.identityId = clientResult.IdentityId;
        this._identityIdStore.storeIdentityId({
          id: clientResult.IdentityId,
          type: "primary"
        });
      }
      this._credentialsAndIdentityId = {
        ...res,
        isAuthenticatedCreds: true,
        associatedIdToken: (_c = authTokens.idToken) == null ? void 0 : _c.toString()
      };
      return res;
    } else {
      throw new AuthError({
        name: "CredentialsException",
        message: `Cognito did not respond with either Credentials, AccessKeyId or SecretKey.`
      });
    }
  }
  isPastTTL() {
    return this._nextCredentialsRefresh === void 0 ? true : this._nextCredentialsRefresh <= Date.now();
  }
  hasTokenChanged(tokens) {
    var _a, _b;
    return !!tokens && !!((_a = this._credentialsAndIdentityId) == null ? void 0 : _a.associatedIdToken) && ((_b = tokens.idToken) == null ? void 0 : _b.toString()) !== this._credentialsAndIdentityId.associatedIdToken;
  }
};

// node_modules/aws-amplify/node_modules/@aws-amplify/auth/dist/esm/providers/cognito/credentialsProvider/index.mjs
var cognitoCredentialsProvider = new CognitoAWSCredentialsAndIdentityIdProvider(new DefaultIdentityIdStore(defaultStorage));

// node_modules/aws-amplify/dist/esm/initSingleton.mjs
var DefaultAmplify = {
  /**
   * Configures Amplify with the {@link resourceConfig} and {@link libraryOptions}.
   *
   * @param resourceConfig The {@link ResourcesConfig} object that is typically imported from the
   * `amplifyconfiguration.json` file. It can also be an object literal created inline when calling `Amplify.configure`.
   * @param libraryOptions The {@link LibraryOptions} additional options for the library.
   *
   * @example
   * import config from './amplifyconfiguration.json';
   *
   * Amplify.configure(config);
   */
  configure(resourceConfig, libraryOptions) {
    const resolvedResourceConfig = parseAmplifyConfig(resourceConfig);
    const cookieBasedKeyValueStorage = new CookieStorage({ sameSite: "lax" });
    const resolvedKeyValueStorage = (libraryOptions == null ? void 0 : libraryOptions.ssr) ? cookieBasedKeyValueStorage : defaultStorage;
    const resolvedCredentialsProvider = (libraryOptions == null ? void 0 : libraryOptions.ssr) ? new CognitoAWSCredentialsAndIdentityIdProvider(new DefaultIdentityIdStore(cookieBasedKeyValueStorage)) : cognitoCredentialsProvider;
    if (!resolvedResourceConfig.Auth) {
      Amplify.configure(resolvedResourceConfig, libraryOptions);
      return;
    }
    if (libraryOptions == null ? void 0 : libraryOptions.Auth) {
      Amplify.configure(resolvedResourceConfig, libraryOptions);
      return;
    }
    if (!Amplify.libraryOptions.Auth) {
      cognitoUserPoolsTokenProvider.setAuthConfig(resolvedResourceConfig.Auth);
      cognitoUserPoolsTokenProvider.setKeyValueStorage(
        // TODO: allow configure with a public interface
        resolvedKeyValueStorage
      );
      Amplify.configure(resolvedResourceConfig, {
        ...libraryOptions,
        Auth: {
          tokenProvider: cognitoUserPoolsTokenProvider,
          credentialsProvider: resolvedCredentialsProvider
        }
      });
      return;
    }
    if (libraryOptions) {
      const authLibraryOptions = Amplify.libraryOptions.Auth;
      if (libraryOptions.ssr !== void 0) {
        cognitoUserPoolsTokenProvider.setKeyValueStorage(
          // TODO: allow configure with a public interface
          resolvedKeyValueStorage
        );
        authLibraryOptions.credentialsProvider = resolvedCredentialsProvider;
      }
      Amplify.configure(resolvedResourceConfig, {
        Auth: authLibraryOptions,
        ...libraryOptions
      });
      return;
    }
    Amplify.configure(resolvedResourceConfig);
  },
  /**
   * Returns the {@link ResourcesConfig} object passed in as the `resourceConfig` parameter when calling
   * `Amplify.configure`.
   *
   * @returns An {@link ResourcesConfig} object.
   */
  getConfig() {
    return Amplify.getConfig();
  }
};
export {
  DefaultAmplify as Amplify
};
//# sourceMappingURL=aws-amplify.js.map
