import React, { useEffect, useMemo, useRef } from "react";
import ReactMarkdown, { Components } from "react-markdown";
import type { PluggableList } from "unified";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeHighlight from "rehype-highlight";
import { useHighlightLanguages } from "@/hooks/useHighlightLanguages";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

import { useTypewriter } from "@/hooks/useTypewriter";
import {
  ChatPacket,
  PacketType,
  StopReason,
} from "../../../services/streamingModels";
import { MessageRenderer, FullChatState } from "../interfaces";
import { isFinalAnswerComplete } from "../../../services/packetUtils";
import { processContent, ScrollableTable } from "../markdownUtils";
import { BlinkingBar } from "../../BlinkingBar";
import {
  MemoizedAnchor,
  MemoizedParagraph,
} from "@/app/app/message/MemoizedTextComponents";
import { extractCodeText } from "@/app/app/message/codeUtils";
import { CodeBlock } from "@/app/app/message/CodeBlock";
import { InMessageImage } from "@/app/app/components/files/images/InMessageImage";
import { extractChatImageFileId } from "@/app/app/components/files/images/utils";
import { transformLinkUri } from "@/lib/utils";
import { cn } from "@opal/utils";
import { useSmoothStreaming } from "@/hooks/useSmoothStreaming";
import { useChatSessionStore } from "@/app/app/stores/useChatSessionStore";

// Streaming pipeline runs gfm + math so LaTeX renders live.
// Syntax highlighting is the heavier of the two and stays deferred —
// rehype-highlight only flips in once the stream is fully displayed.
const STREAMING_REMARK_PLUGINS: PluggableList = [
  remarkGfm,
  [remarkMath, { singleDollarTextMath: true }],
];
const STREAMING_REHYPE_PLUGINS: PluggableList = [rehypeKatex];
const FULL_REMARK_PLUGINS: PluggableList = STREAMING_REMARK_PLUGINS;

export const MessageTextRenderer: MessageRenderer<
  ChatPacket,
  FullChatState
> = ({
  packets,
  state,
  messageNodeId,
  hasTimelineThinking,
  onComplete,
  renderType,
  animate,
  stopPacketSeen,
  stopReason,
  children,
}) => {
  const { enabled: smoothStreamingEnabled } = useSmoothStreaming();
  const setLatestMessageRenderComplete = useChatSessionStore(
    (state) => state.setLatestMessageRenderComplete
  );
  const setIsStreamDraining = useChatSessionStore(
    (state) => state.setIsStreamDraining
  );

  const lastVisibleContentRef = useRef("");

  const fullContent = packets
    .map((packet) => {
      if (
        packet.obj.type === PacketType.MESSAGE_DELTA ||
        packet.obj.type === PacketType.MESSAGE_START
      ) {
        return packet.obj.content;
      }
      return "";
    })
    .join("");

  // Freeze on user cancel: once generation is cancelled, keep showing the
  // last content that was actually visible instead of snapping to whatever
  // partial content happened to be in the final packets.
  const content = useMemo(() => {
    const wasUserCancelled = stopReason === StopReason.USER_CANCELLED;

    if (wasUserCancelled && animate) {
      return lastVisibleContentRef.current;
    }

    return fullContent;
  }, [fullContent, stopReason, animate]);

  useEffect(() => {
    if (content.length > 0) {
      lastVisibleContentRef.current = content;
    }
  }, [content]);

  const isStreamingAnimationEnabled =
    animate &&
    stopReason !== StopReason.USER_CANCELLED &&
    smoothStreamingEnabled;

  const isStreamFinished = isFinalAnswerComplete(packets);

  const { displayed: displayedContent, isDraining } = useTypewriter(
    content,
    isStreamingAnimationEnabled,
    isStreamFinished
  );

  // One-way signal: stream done AND typewriter caught up. Do NOT derive
  // this from "typewriter currently behind" — it oscillates mid-stream
  // between packet bursts and would thrash the plugin pipeline.
  const streamFullyDisplayed =
    isStreamFinished && displayedContent.length >= content.length;

  // Syntax-highlighting grammars load dynamically, and only once the stream is
  // fully displayed — keeps the ~170 KB corpus off the critical path. Until
  // they resolve we fall back to the streaming (katex-only) plugin set.
  const highlightLanguages = useHighlightLanguages(streamFullyDisplayed);
  const fullRehypePlugins = useMemo<PluggableList>(
    () =>
      highlightLanguages
        ? [[rehypeHighlight, { languages: highlightLanguages }], rehypeKatex]
        : STREAMING_REHYPE_PLUGINS,
    [highlightLanguages]
  );

  // Capture `animate` at mount. `animate = !stopPacketSeen`, which only
  // ever goes true→false during a renderer's lifetime, so its mount-time
  // value distinguishes "actively-streaming renderer" (animate=true) from
  // "historical mount" (animate=false). Used to gate the queue-release
  // write below.
  const wasEverAnimatingRef = useRef(animate);

  // Bind sessionId at mount so a navigation while the typewriter is still
  // draining doesn't write the completion flag to the newly-active session.
  const sessionIdAtMountRef = useRef(
    useChatSessionStore.getState().currentSessionId
  );

  // Fire onComplete exactly once per mount. `onComplete` is an inline
  // arrow in AgentMessage so its identity changes on every parent render;
  // without this guard, each new identity would re-fire the effect once
  // `streamFullyDisplayed` is true.
  const onCompleteFiredRef = useRef(false);
  useEffect(() => {
    if (streamFullyDisplayed && !onCompleteFiredRef.current) {
      onCompleteFiredRef.current = true;
      onComplete();
      // Only the renderer that was actively streaming (mounted with
      // animate=true) flips the chat-session gate back to "rendered".
      // Historical mounts leave the flag alone so they don't release the
      // queue while a newer stream is still in flight.
      if (wasEverAnimatingRef.current && sessionIdAtMountRef.current) {
        setLatestMessageRenderComplete(sessionIdAtMountRef.current, true);
      }
    }
  }, [streamFullyDisplayed, onComplete, setLatestMessageRenderComplete]);

  // Mirror the typewriter's drain state into the chat-session store so
  // ChatScrollContainer can pause auto-scroll while the drain runs. Only
  // the actively-animating renderer writes — historical mounts never
  // enter the drain branch in useTypewriter.
  useEffect(() => {
    if (!wasEverAnimatingRef.current || !sessionIdAtMountRef.current) return;
    setIsStreamDraining(sessionIdAtMountRef.current, isDraining);
  }, [isDraining, setIsStreamDraining]);

  const processedContent = useMemo(
    () => processContent(displayedContent),
    [displayedContent]
  );

  // Stable-identity components for ReactMarkdown. Dynamic data (`state`,
  // `processedContent`) flows through refs so the callback identities
  // never change — otherwise every typewriter tick would invalidate
  // React reconciliation on the markdown subtree.
  const stateRef = useRef(state);
  stateRef.current = state;
  const processedContentRef = useRef(processedContent);
  processedContentRef.current = processedContent;

  const markdownComponents = useMemo<Components>(
    () => ({
      a: ({ href, children }) => {
        const s = stateRef.current;
        const imageFileId = extractChatImageFileId(
          href,
          String(children ?? "")
        );
        if (imageFileId) {
          return (
            <InMessageImage
              fileId={imageFileId}
              fileName={String(children ?? "")}
            />
          );
        }
        return (
          <MemoizedAnchor
            updatePresentingDocument={s?.setPresentingDocument || (() => {})}
            docs={s?.docs || []}
            userFiles={s?.userFiles || []}
            citations={s?.citations}
            href={href}
          >
            {children}
          </MemoizedAnchor>
        );
      },
      p: ({ children }) => (
        <MemoizedParagraph className="font-main-content-body">
          {children}
        </MemoizedParagraph>
      ),
      pre: ({ children }) => <>{children}</>,
      b: ({ className, children }) => (
        <span className={className}>{children}</span>
      ),
      ul: ({ className, children, ...rest }) => (
        <ul className={className} {...rest}>
          {children}
        </ul>
      ),
      ol: ({ className, children, ...rest }) => (
        <ol className={className} {...rest}>
          {children}
        </ol>
      ),
      li: ({ className, children, ...rest }) => (
        <li className={className} {...rest}>
          {children}
        </li>
      ),
      table: ({ className, children, ...rest }) => (
        <ScrollableTable className={className} {...rest}>
          {children}
        </ScrollableTable>
      ),
      code: ({ node, className, children }) => {
        const codeText = extractCodeText(
          node,
          processedContentRef.current,
          children
        );
        return (
          <CodeBlock className={className} codeText={codeText}>
            {children}
          </CodeBlock>
        );
      },
    }),
    []
  );

  const shouldShowCursor =
    displayedContent.length > 0 &&
    ((isStreamingAnimationEnabled && !streamFullyDisplayed) ||
      (!isStreamingAnimationEnabled && !stopPacketSeen));

  // `[*]() ` is rendered by the anchor component as an inline blinking
  // caret, keeping it flush with the trailing character.
  const markdownInput = shouldShowCursor
    ? processedContent + " [*]() "
    : processedContent;

  return children([
    {
      icon: null,
      status: null,
      content:
        displayedContent.length > 0 ? (
          <div
            dir="auto"
            className={cn(!streamFullyDisplayed && "streaming-katex")}
          >
            <ReactMarkdown
              className="prose prose-orbyte font-main-content-body max-w-full"
              components={markdownComponents}
              remarkPlugins={
                streamFullyDisplayed
                  ? FULL_REMARK_PLUGINS
                  : STREAMING_REMARK_PLUGINS
              }
              rehypePlugins={
                streamFullyDisplayed
                  ? fullRehypePlugins
                  : STREAMING_REHYPE_PLUGINS
              }
              urlTransform={transformLinkUri}
            >
              {markdownInput}
            </ReactMarkdown>
          </div>
        ) : (
          <BlinkingBar addMargin />
        ),
    },
  ]);
};
