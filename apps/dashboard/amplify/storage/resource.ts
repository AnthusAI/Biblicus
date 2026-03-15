import { defineStorage } from '@aws-amplify/backend';

export const storage = defineStorage({
  name: 'biblicusCorpus',
  access: (allow) => ({
    'corpus/{entity_id}/*': [
      allow.entity('identity').to(['read', 'write', 'delete']),
    ],
    'public/*': [
      allow.guest.to(['read']),
      allow.authenticated.to(['read', 'write']),
    ],
  }),
});
