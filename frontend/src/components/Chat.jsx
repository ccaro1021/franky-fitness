import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { sendMessage } from '../api'
import MealPlanCard from './MealPlanCard'
import RecipeCard from './RecipeCard'
import GroceryListCard from './GroceryListCard'
import WorkoutPlanCard from './WorkoutPlanCard'

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white text-xs font-bold mr-2 shrink-0 mt-0.5">
          F
        </div>
      )}
      <div className={`${isUser ? 'max-w-[75%] items-end' : 'max-w-[90%] items-start'} flex flex-col`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? 'bg-emerald-600 text-white rounded-br-sm whitespace-pre-wrap'
              : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm overflow-x-auto'
          }`}
        >
          {isUser ? (
            msg.content
          ) : (
            <div className="prose prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-table:text-xs prose-th:px-2 prose-td:px-2 prose-ul:my-1 prose-ol:my-1">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>
          )}
        </div>
        {msg.meal_plan && <MealPlanCard plan={msg.meal_plan} />}
        {msg.recipe && <RecipeCard recipe={msg.recipe} />}
        {msg.grocery_list && <GroceryListCard groceryList={msg.grocery_list} />}
        {msg.workout_plan && <WorkoutPlanCard plan={msg.workout_plan} />}
      </div>
    </div>
  )
}

export default function Chat({ user }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `Hi ${user.name}! I'm Franky, your nutrition and training coach. What can I help you with this week? I can build a meal plan, suggest recipes, generate a grocery list, or put together a workout plan.`,
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function handleSend() {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { role: 'user', content: text }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput('')
    setLoading(true)
    setError(null)

    // Build the API payload — only role/content pairs, no meal_plan metadata
    const apiMessages = nextMessages.map(m => ({ role: m.role, content: m.content }))

    try {
      const data = await sendMessage(apiMessages)
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: data.message,
          meal_plan: data.meal_plan || null,
          recipe: data.recipe || null,
          grocery_list: data.grocery_list || null,
          workout_plan: data.workout_plan || null,
        },
      ])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.map((msg, i) => (
          <Message key={i} msg={msg} />
        ))}

        {loading && (
          <div className="flex justify-start mb-4">
            <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white text-xs font-bold mr-2 shrink-0">
              F
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1 items-center">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="text-center text-sm text-red-500 mb-4 bg-red-50 rounded-lg px-4 py-2">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white px-4 py-3">
        <div className="flex gap-2 items-end">
          <textarea
            className="flex-1 resize-none border border-gray-200 rounded-xl px-3 py-2.5 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent max-h-32"
            rows={1}
            placeholder="Message Franky…"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="px-4 py-2.5 bg-emerald-600 text-white rounded-xl text-sm font-medium hover:bg-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
          >
            Send
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-1.5 text-center">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
