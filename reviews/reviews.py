from db import VideoTranscription, Review
from sqlmodel import Session, select, desc, asc

class ReviewCRUD:
    
    @staticmethod
    def create_review(session: Session, review_data: dict) -> Review:
        transcription_id = review_data.get('transcription_id')
        if transcription_id is not None:
            transcription = session.get(VideoTranscription, transcription_id)
            if not transcription:
                raise ValueError(f"transcription_id not found")
        rating = review_data.get('rating')
        if rating is not None and not (1 <= rating <= 5):
            raise ValueError("The rating should be from 1 to 5")
        comment = review_data.get('comment', '')
        if len(comment) > 2000:
            raise ValueError("The review must not exceed 2000 characters.")
        review = Review(**review_data)
        session.add(review)
        session.commit()
        session.refresh(review)
        return review
    
    def get_service_reviews(
        session: Session,
        limit: int = 10,
        sort_by: str = "newest"
    ) -> List[Review]:
        
        if limit < 1 or limit > 100:
            raise ValueError("The limit should be from 1 to 100")
        if sort_by not in ["newest", "oldest", "best", "worst"]:
            raise ValueError("Incorrect sorting parameter")        
        
        statement = select(Review).where(Review.transcription_id.is_(None))
        
        if sort_by == "newest":
            statement = statement.order_by(desc(Review.created_dt_tm))
        elif sort_by == "oldest":
            statement = statement.order_by(asc(Review.created_dt_tm))
        elif sort_by == "best":
            statement = statement.order_by(
                desc(Review.rating), 
                desc(Review.created_dt_tm)
            )
        elif sort_by == "worst":
            statement = statement.order_by(
                asc(Review.rating), 
                desc(Review.created_dt_tm)
            )
        
        statement = statement.limit(limit)
        return session.exec(statement).all()
    
    @staticmethod
    def get_transcription_reviews(
        session: Session,
        transcription_id: int,
        limit: int = 10,
        sort_by: str = "newest"
    ) -> List[Review]:
        if limit < 1 or limit > 100:
            raise ValueError("The limit should be from 1 to 100")
        if sort_by not in ["newest", "oldest", "best", "worst"]:
            raise ValueError("Incorrect sorting parameter")
        
        transcription = session.get(VideoTranscription, transcription_id)
        if not transcription:
            raise ValueError(f"transcription_id not found")
        
        statement = select(Review).where(
            Review.transcription_id == transcription_id
        )
        
        if sort_by == "newest":
            statement = statement.order_by(desc(Review.created_dt_tm))
        elif sort_by == "oldest":
            statement = statement.order_by(asc(Review.created_dt_tm))
        elif sort_by == "best":
            statement = statement.order_by(
                desc(Review.rating), 
                desc(Review.created_dt_tm)
            )
        elif sort_by == "worst":
            statement = statement.order_by(
                asc(Review.rating), 
                desc(Review.created_dt_tm)
            )
        
        statement = statement.limit(limit)
        return session.exec(statement).all()
