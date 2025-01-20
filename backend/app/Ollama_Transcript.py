from chromadb import Client as ChromaClient, Settings
from pydantic import BaseModel
from typing import List, Dict, Optional
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.ollama import OllamaModel
import json
import logging
import uuid
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()  # Load environment variables from .env file

class Block(BaseModel):
    """Represents a block of content in a section"""
    id: str
    type: str
    content: str
    color: str

class Section(BaseModel):
    """Represents a section in the meeting summary"""
    title: str
    blocks: List[Block]

class ActionItem(BaseModel):
    """Represents an action item from the meeting"""
    title: str
    content: str

class SummaryResponse(BaseModel):
    """Represents the complete meeting summary"""
    Agenda: Section
    Decisions: Section
    ActionItems: Section
    ClosingRemarks: Section

class TranscriptProcessor:
    """Handles the processing and storage of meeting transcripts"""
    def __init__(self):
        """Initialize the transcript processor"""
        self.collection_name = "all_transcripts"
        self.chroma_client = None
        self.collection = None
        self.initialize_collection()

    def __del__(self):
        """Cleanup ChromaDB connection"""
        if self.chroma_client:
            try:
                self.collection = None
                self.chroma_client = None
            except Exception as e:
                logger.error(f"Error cleaning up ChromaDB: {e}")

    def initialize_collection(self):
        """Initialize or get the ChromaDB collection"""
        try:
            if self.chroma_client:
                self.collection = None
                self.chroma_client = None
                
            # Create new client with settings
            settings = Settings(
                allow_reset=True,
                is_persistent=True
            )
            self.chroma_client = ChromaClient(settings)
            
            try:
                # Try to get existing collection
                self.collection = self.chroma_client.get_collection(name=self.collection_name)
                logger.info(f"Retrieved existing collection: {self.collection_name}")
            except Exception:
                # Create new collection if it doesn't exist
                logger.info(f"Creating new collection: {self.collection_name}")
                self.collection = self.chroma_client.create_collection(name=self.collection_name)
            
            if not self.collection:
                raise RuntimeError("Failed to initialize ChromaDB collection")
                
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            raise
    
    def cleanup(self):
        """Cleanup ChromaDB resources"""
        if self.chroma_client:
            try:
                self.collection = None
                self.chroma_client = None
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
    
    def process_transcript(self, transcript_path: str, chunk_size: int = 5000, overlap: int = 1000):
        """Process and store transcript in chunks"""
        try:
            # Clear any existing collection
            if self.collection:
                try:
                    self.collection.delete(ids=self.collection.get()['ids'])
                except Exception as e:
                    logger.error(f"Error clearing collection: {e}")
            
            # If transcript_path is a string that is a path name, use it, else if transcript is plain text, use it
            if isinstance(transcript_path, str):
                if os.path.exists(transcript_path):
                    with open(transcript_path, 'r') as f:
                        transcript = f.read()
                else:
                    transcript = transcript_path
            else:
                transcript = transcript_path
            
            # Split transcript into chunks
            chunks = [transcript[i:i+chunk_size] for i in range(0, len(transcript), chunk_size-overlap)]
            
            # Add chunks to collection
            if not self.collection:
                self.initialize_collection()
                
            for i, chunk in enumerate(chunks):
                self.collection.add(
                    documents=[chunk],
                    metadatas=[{"source": f"chunk_{i}", "processed": False}],
                    ids=[f"id_{i}"]
                )
            
            logger.info(f"Added {len(chunks)} chunks to collection")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Error processing transcript: {e}")
            raise

class MeetingSummarizer:
    """Handles the meeting summarization using AI models"""
    def __init__(self, api_key: str):
        # self.model = AnthropicModel('claude-3-5-sonnet-latest', api_key=api_key)
        # self.model = OllamaModel('llama3.1:8b')
        self.model = OllamaModel('qwen2.5:14b')

        self.Agenda = Section(title="Agenda", blocks=[])
        self.Decisions = Section(title="Decisions", blocks=[])
        self.ActionItems = Section(title="Action Items", blocks=[])
        self.ClosingRemarks = Section(title="Closing Remarks", blocks=[])
        
    def create_block(self, title: str, content: str, block_type: str = "item", color: str = "default") -> Block:
        """Create a new block with a unique ID"""
        return Block(
            id=str(uuid.uuid4()),
            type=block_type,
            content=content,
            color=color
        )
        
    def add_action_item(self, ctx: RunContext, title: str, content: str):
        """Add an action item to the summary"""
        block = self.create_block(title, content, "action")
        self.ActionItems.blocks.append(block)
        return f"Successfully added action item: {block.id}"
        
    def add_agenda_item(self, ctx: RunContext, title: str, content: str):
        """Add an agenda item to the summary"""
        block = self.create_block(title, content, "agenda")
        self.Agenda.blocks.append(block)
        return f"Successfully added agenda item: {block.id}"
        
    def add_decision(self, ctx: RunContext, title: str, content: str):
        """Add a decision to the summary"""
        block = self.create_block(title, content, "decision")
        self.Decisions.blocks.append(block)
        return f"Successfully added decision: {block.id}"
        
    def generate_summary(self, ctx: RunContext) -> SummaryResponse:
        """Generate the final summary response"""
        return SummaryResponse(
            Agenda=self.Agenda,
            Decisions=self.Decisions,
            ActionItems=self.ActionItems,
            ClosingRemarks=Section(title="Closing Remarks", blocks=[])
        )

SYSTEM_PROMPT = """You are a meeting summarizer agent. Your task is to:

1. EXTRACT INFORMATION
- Use query_transcript to get information about the meeting
- Ask one question at a time and wait for the response
- Process each response completely before making the next tool call
- IMPORTANT: Make only ONE tool call at a time and wait for its response
- If query_transcript returns "CHROMADB_EMPTY", proceed to finalization

2. ORGANIZE INFORMATION
After gathering information, organize it into:
- Agenda items (use add_agenda_item ONE at a time)
- Key decisions made (use add_decision ONE at a time)
- Action items assigned (use add_action_item ONE at a time)
- Any other important points

3. SAVE AND FINALIZE
- Use tools sequentially, waiting for each response
- Once all information is processed, call delete_processed_chunks
- Finally call get_final_summary

Available tools:
- query_transcript
- add_action_item
- add_agenda_item
- add_decision
- save_final_summary_result
- get_final_summary
- delete_processed_chunks

The transcript is stored in ChromaDB - use query_transcript to access it.
Remember to make only ONE tool call at a time and wait for its response.
If you get CHROMADB_EMPTY: All chunks have been processed,
please save the summary to a file and end the process by calling final_result.

Do not run after CHROMADB_EMPTY is received.
"""

# Initialize components
summarizer = MeetingSummarizer(api_key=os.getenv("ANTHROPIC_API_KEY"))
processor = TranscriptProcessor()

# Create an agent first
agent = Agent(
    summarizer.model, 
    result_type=SummaryResponse, 
    result_retries=15, 
    system_prompt=SYSTEM_PROMPT
)

# Define tools
@agent.tool
async def query_transcript(ctx: RunContext, query: str) -> str:
    """Query the transcript to extract information. Returns the content and chunk IDs for deletion."""
    try:
        # Check if there are any chunks left
        collection_data = processor.collection.get()
        if not collection_data['ids']:
            return "CHROMADB_EMPTY: All chunks have been processed."
            
        # Get unprocessed chunks
        results = processor.collection.query(
            query_texts=[query],
            n_results=1
        )
        
        if not results or not results['documents'] or not results['documents'][0]:
            return "No results found for the query"
            
        # Process and immediately delete chunks
        combined_result = ""
        chunk_ids = []
        
        for doc, metadata, id in zip(results['documents'][0], results['metadatas'][0], results['ids'][0]):
            combined_result += f"\n{doc}\n"
            chunk_ids.append(id)
        
        # Delete the chunks we just processed
        if chunk_ids:
            try:
                processor.collection.delete(ids=chunk_ids)
                logger.info(f"Deleted {len(chunk_ids)} processed chunks")
                
                # Verify deletion
                remaining = processor.collection.get()
                logger.info(f"Remaining chunks: {len(remaining['ids'])}")
                
            except Exception as e:
                logger.error(f"Error deleting chunks: {e}")
                return f"Error deleting chunks: {str(e)}"
            
        return combined_result.strip()
        
    except Exception as e:
        logger.error(f"Error querying transcript: {e}")
        return f"Error: {str(e)}"

@agent.tool
async def delete_processed_chunks(ctx: RunContext) -> str:
    """Delete all processed chunks from the collection"""
    try:
        if not hasattr(ctx, 'processed_chunks') or not ctx.processed_chunks:
            return "No chunks to delete"
            
        chunk_ids = list(ctx.processed_chunks)
        processor.collection.delete(ids=chunk_ids)
        
        # Clear the processed chunks
        ctx.processed_chunks.clear()
        
        return f"Successfully deleted {len(chunk_ids)} chunks"
        
    except Exception as e:
        logger.error(f"Error deleting chunks: {e}")
        return f"Error deleting chunks: {str(e)}"

@agent.tool
async def add_action_item(ctx: RunContext, title: str, content: str) -> str:
    """Add an action item to the summary"""
    result = summarizer.add_action_item(ctx, title, content)
    return f"Successfully added action item: {result}"

@agent.tool
async def add_agenda_item(ctx: RunContext, title: str, content: str) -> str:
    """Add an agenda item to the summary"""
    result = summarizer.add_agenda_item(ctx, title, content)
    return f"Successfully added agenda item: {result}"

@agent.tool
async def add_decision(ctx: RunContext, title: str, content: str) -> str:
    """Add a decision to the summary"""
    result = summarizer.add_decision(ctx, title, content)
    return f"Successfully added decision: {result}"

@agent.tool
async def save_final_summary_result(ctx: RunContext) -> str:
    """
    Save the final meeting summary result to a file
    args:
        ctx (RunContext): The run context

    returns:    
        str: Status message indicating success or failure
    """
    try:
        # Get the final summary result
        summary = summarizer.generate_summary(ctx)
        
        # Validate summary has content
        if not any([
            summary.Agenda.blocks,
            summary.Decisions.blocks,
            summary.ActionItems.blocks,
            summary.ClosingRemarks.blocks
        ]):
            return "Error: No content found in summary. Please add some items first."

        # Convert to JSON using Pydantic's json() method which handles nested models
        json_data = summary.model_dump_json(indent=2)
        
        # Save to file with error handling
        try:
            with open('final_summary_result.json', 'w') as f:
                f.write(json_data)
            return "Successfully saved final summary result to file"
        except IOError as e:
            logger.error(f"Failed to write summary to file: {e}")
            return f"Error saving to file: {str(e)}"
            
    except Exception as e:
        logger.error(f"Error generating or saving summary: {e}")
        return f"Error processing summary: {str(e)}"

@agent.tool
async def get_final_summary(ctx: RunContext) -> SummaryResponse:
    """Get the final meeting summary result"""
    return summarizer.generate_summary(ctx)

# Update agent with tools after they are defined
agent.tools = [
    query_transcript,
    add_action_item,
    add_agenda_item,
    add_decision,
    save_final_summary_result,
    get_final_summary,
    delete_processed_chunks
]

logger.info("Initialized QA Agent")

def pretty_print_json(obj):
    """Utility function to pretty print JSON objects"""
    if hasattr(obj, 'model_dump_json'):
        print(obj.model_dump_json(indent=2))
    else:
        print(json.dumps(obj, indent=2))

# Example usage
if __name__ == "__main__":
    try:
        # Process a transcript
        num_chunks = processor.process_transcript('../transcripts/susi_transcript.txt')
        logger.info(f"Processed transcript into {num_chunks} chunks")
        
        # Run the summary with proper tool response handling
        summary = agent.run_sync(
            'What is the summary of the following meeting? Please process one query at a time and wait for responses.'
        )
        
        # Handle the summary result
        if hasattr(summary, 'data'):
            pretty_print_json(summary.data)
        else:
            pretty_print_json(summary)
            
    except Exception as e:
        logger.error(f"Error during summarization: {str(e)}")
        processor.cleanup()