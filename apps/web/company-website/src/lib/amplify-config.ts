import { Amplify } from "aws-amplify";

const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId:
        process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || "",
      userPoolClientId:
        process.env.NEXT_PUBLIC_COGNITO_APP_CLIENT_ID || "",
    },
  },
};

export function configureAmplify() {
  console.log("Configuring Amplify with:", {
    userPoolId:
      process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID,
    clientId: process.env.NEXT_PUBLIC_COGNITO_APP_CLIENT_ID,
  });

  Amplify.configure(amplifyConfig, { ssr: true });
}
