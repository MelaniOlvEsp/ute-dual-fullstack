import test from 'node:test'
import assert from 'node:assert/strict'
import { prepareMessage } from '../src/domain/foro/messages.js'
import { createForumUseCases } from '../src/application/use-cases/forum.js'

test('mailbox only accepts Dual', () => {
  assert.deepEqual(prepareMessage({ area: 'dual', asunto: '  Consulta ', mensaje: ' Hola ' }), {
    area: 'dual', asunto: 'Consulta', mensaje: 'Hola'
  })
  assert.throws(() => prepareMessage({area:'externa', asunto:'Hola', mensaje:'Texto'}), /Área/)
  assert.throws(() => prepareMessage({area:'dual', asunto:'Hi', mensaje:'Texto'}), /asunto/)
})

test('rejected mailbox area never reaches the repository', async () => {
  let called = false
  const useCases = createForumUseCases({
    posts: {}, mailbox: { listar: async () => { called = true } }
  })
  assert.throws(() => useCases.buzon.listar('externa'))
  assert.equal(called, false)
})

test('forbidden reactions are rejected before calling the API', () => {
  const useCases = createForumUseCases({ posts: {}, mailbox: {} })
  assert.throws(() => useCases.foro.reaccionar(1, 'unknown'), /Reacción/)
})
